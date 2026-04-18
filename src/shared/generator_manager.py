"""Generator manager — wraps both Epic and Network generators as controllable
background processes with start/stop/status semantics.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("shared.generator_manager")

# Paths relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_EPIC_SRC = _PROJECT_ROOT / "src" / "epic_generator"
_NETWORK_SRC = _PROJECT_ROOT / "src" / "network_generator"
_CONFIG_ROOT = _PROJECT_ROOT / "config"


@dataclass
class GeneratorStatus:
    name: str
    running: bool = False
    pid: int | None = None
    started_at: str | None = None
    events_generated: int = 0
    error: str | None = None


def _run_epic_generator(
    config_dir: str,
    output_dir: str,
    environment: str,
    generators_enabled: list[str] | None,
    tick_interval: int,
    stop_event: multiprocessing.Event,
):
    """Entry point for the Epic generator subprocess."""
    # Add epic source to path so imports resolve
    sys.path.insert(0, str(_EPIC_SRC))
    os.chdir(str(_EPIC_SRC))

    from orchestrator import Orchestrator
    from outputs.file_output import FileOutput

    output = FileOutput(output_dir)
    orch = Orchestrator(
        config_dir=config_dir,
        output=output,
        generators_enabled=generators_enabled,
    )

    logger.info("Epic generator started (pid=%d)", os.getpid())
    try:
        while not stop_event.is_set():
            events = orch.tick()
            stop_event.wait(timeout=tick_interval)
    except Exception as exc:
        logger.exception("Epic generator error: %s", exc)
    finally:
        logger.info("Epic generator stopped")


def _run_network_generator(
    topology_path: str,
    output_dir: str,
    scenarios: list[str],
    tick_interval: int,
    mode: str,
    duration: int,
    stop_event: multiprocessing.Event,
):
    """Entry point for the Network generator subprocess."""
    sys.path.insert(0, str(_NETWORK_SRC.parent))
    os.chdir(str(_NETWORK_SRC))

    # Use the CLI programmatically via click's invoke
    from network_generator.cli import generate
    from click.testing import CliRunner

    args = [
        "--config", topology_path,
        "--output", "file",
        "--output-dir", output_dir,
        "--mode", mode,
        "--duration", str(duration),
        "--tick-interval", str(tick_interval),
    ]
    for s in scenarios:
        args.extend(["--scenario", s])

    runner = CliRunner()
    result = runner.invoke(generate, args)
    if result.exit_code != 0:
        logger.error("Network generator failed: %s", result.output)


class GeneratorManager:
    """Manages Epic and Network generator processes."""

    def __init__(
        self,
        output_dir: str = "output",
        epic_config_dir: str | None = None,
        network_topology: str | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.epic_config_dir = epic_config_dir or str(_EPIC_SRC / "config")
        self.network_topology = network_topology or str(
            _CONFIG_ROOT / "hospital" / "topology.yaml"
        )

        self._epic_process: multiprocessing.Process | None = None
        self._network_process: multiprocessing.Process | None = None
        self._epic_stop = multiprocessing.Event()
        self._network_stop = multiprocessing.Event()

        self._epic_started: str | None = None
        self._network_started: str | None = None

        # Generator configuration
        self.epic_config: dict[str, Any] = {
            "generators_enabled": None,  # None = all
            "tick_interval": 10,
            "environment": "PRD",
        }
        self.network_config: dict[str, Any] = {
            "scenarios": [],
            "tick_interval": 60,
            "mode": "realtime",
            "duration": 3600,
        }

    # ── Epic Generator ────────────────────────────────────────────

    def start_epic(self) -> GeneratorStatus:
        if self._epic_process and self._epic_process.is_alive():
            return self.epic_status()

        self._epic_stop.clear()
        self._epic_process = multiprocessing.Process(
            target=_run_epic_generator,
            kwargs={
                "config_dir": self.epic_config_dir,
                "output_dir": str(self.output_dir / "epic"),
                "environment": self.epic_config["environment"],
                "generators_enabled": self.epic_config["generators_enabled"],
                "tick_interval": self.epic_config["tick_interval"],
                "stop_event": self._epic_stop,
            },
            daemon=True,
            name="epic-generator",
        )
        self._epic_process.start()
        self._epic_started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        logger.info("Started Epic generator (pid=%d)", self._epic_process.pid)
        return self.epic_status()

    def stop_epic(self) -> GeneratorStatus:
        if self._epic_process and self._epic_process.is_alive():
            self._epic_stop.set()
            self._epic_process.join(timeout=10)
            if self._epic_process.is_alive():
                self._epic_process.terminate()
            logger.info("Stopped Epic generator")
        self._epic_started = None
        return self.epic_status()

    def epic_status(self) -> GeneratorStatus:
        running = bool(self._epic_process and self._epic_process.is_alive())
        return GeneratorStatus(
            name="epic",
            running=running,
            pid=self._epic_process.pid if running else None,
            started_at=self._epic_started if running else None,
        )

    # ── Network Generator ─────────────────────────────────────────

    def start_network(self) -> GeneratorStatus:
        if self._network_process and self._network_process.is_alive():
            return self.network_status()

        self._network_stop.clear()
        self._network_process = multiprocessing.Process(
            target=_run_network_generator,
            kwargs={
                "topology_path": self.network_topology,
                "output_dir": str(self.output_dir / "network"),
                "scenarios": self.network_config["scenarios"],
                "tick_interval": self.network_config["tick_interval"],
                "mode": self.network_config["mode"],
                "duration": self.network_config["duration"],
                "stop_event": self._network_stop,
            },
            daemon=True,
            name="network-generator",
        )
        self._network_process.start()
        self._network_started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        logger.info("Started Network generator (pid=%d)", self._network_process.pid)
        return self.network_status()

    def stop_network(self) -> GeneratorStatus:
        if self._network_process and self._network_process.is_alive():
            self._network_stop.set()
            self._network_process.join(timeout=10)
            if self._network_process.is_alive():
                self._network_process.terminate()
            logger.info("Stopped Network generator")
        self._network_started = None
        return self.network_status()

    def network_status(self) -> GeneratorStatus:
        running = bool(self._network_process and self._network_process.is_alive())
        return GeneratorStatus(
            name="network",
            running=running,
            pid=self._network_process.pid if running else None,
            started_at=self._network_started if running else None,
        )

    # ── Convenience ───────────────────────────────────────────────

    def start_all(self) -> dict:
        return {
            "epic": self.start_epic().__dict__,
            "network": self.start_network().__dict__,
        }

    def stop_all(self) -> dict:
        return {
            "epic": self.stop_epic().__dict__,
            "network": self.stop_network().__dict__,
        }

    def status(self) -> dict:
        return {
            "epic": self.epic_status().__dict__,
            "network": self.network_status().__dict__,
        }
