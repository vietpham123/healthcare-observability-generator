"""CLI entry point — orchestrates topology loading, baseline generation,
scenario execution, and output dispatch.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import click

# Force vendor registration by importing the vendors package
import netloggen.vendors  # noqa: F401

from netloggen.core.clock import Clock, ClockMode
from netloggen.core.random_utils import SeededRandom
from netloggen.core.topology import load_topology
from netloggen.outputs.base import BaseOutput
from netloggen.outputs.dynatrace import DynatraceOutput
from netloggen.outputs.file_out import FileOutput
from netloggen.outputs.syslog_out import SyslogOutput
from netloggen.outputs.snmp_out import SNMPTrapOutput
from netloggen.outputs.netflow_out import NetFlowOutput
from netloggen.outputs.http_out import HTTPWebhookOutput
from netloggen.scenarios.baseline import BaselineGenerator
from netloggen.scenarios.engine import ScenarioEngine, load_scenario

logger = logging.getLogger("netloggen")

_SHUTDOWN = False


def _handle_signal(sig, frame):
    global _SHUTDOWN
    _SHUTDOWN = True
    logger.info("Shutdown signal received, finishing current tick...")


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Network Log Generator — high-fidelity synthetic network data for Dynatrace."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command("generate")
@click.option("--config", "-c", type=click.Path(exists=True), required=True,
              help="Path to YAML topology config file.")
@click.option("--scenario", "-s", type=click.Path(exists=True), multiple=True,
              help="Path(s) to scenario YAML playbook(s). Can be repeated.")
@click.option("--output", "-o", type=click.Choice(["file", "dynatrace", "syslog", "snmp", "netflow", "http", "kafka", "both", "all"]),
              default="file", help="Output destination.")
@click.option("--output-dir", type=click.Path(), default="output",
              help="Directory for file output (default: output/).")
@click.option("--output-format", type=click.Choice(["json", "csv", "raw"]), default="json",
              help="File output format (default: json).")
@click.option("--mode", "-m", type=click.Choice(["realtime", "batch"]), default="batch",
              help="Generation mode: realtime (continuous) or batch (one-shot).")
@click.option("--duration", "-d", type=int, default=3600,
              help="Duration in seconds for batch mode (default: 3600).")
@click.option("--tick-interval", type=int, default=60,
              help="Seconds between baseline ticks (default: 60).")
@click.option("--seed", type=int, default=None,
              help="Random seed for reproducible output.")
@click.option("--dt-endpoint", envvar="DT_ENDPOINT", default=None,
              help="Dynatrace endpoint URL (or DT_ENDPOINT env var).")
@click.option("--dt-token", envvar="DT_API_TOKEN", default=None,
              help="Dynatrace API token (or DT_API_TOKEN env var).")
@click.option("--syslog-host", default=None, help="Syslog target host.")
@click.option("--syslog-port", type=int, default=514, help="Syslog target port (default: 514).")
@click.option("--syslog-protocol", type=click.Choice(["udp", "tcp", "tls"]), default="udp")
@click.option("--snmp-host", default=None, help="SNMP trap receiver host.")
@click.option("--snmp-port", type=int, default=162, help="SNMP trap port (default: 162).")
@click.option("--netflow-host", default=None, help="NetFlow collector host.")
@click.option("--netflow-port", type=int, default=2055, help="NetFlow port (default: 2055).")
@click.option("--netflow-version", type=click.Choice(["5", "9", "10"]), default="9")
@click.option("--http-url", default=None, help="HTTP webhook URL.")
@click.option("--kafka-brokers", default=None, help="Kafka bootstrap servers (comma-separated).")
@click.option("--kafka-topic-prefix", default="netloggen", help="Kafka topic prefix.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), default="INFO")
@click.option("--no-baseline", is_flag=True, help="Skip baseline generation (scenarios only).")
@click.option("--dry-run", is_flag=True, help="Generate data but don't send (print stats only).")
@click.option("--snmp-state-path", default=None,
              help="Write SNMP agent state file each tick (enables SNMP agent integration).")
def generate(
    config: str,
    scenario: tuple[str, ...],
    output: str,
    output_dir: str,
    output_format: str,
    mode: str,
    duration: int,
    tick_interval: int,
    seed: int | None,
    dt_endpoint: str | None,
    dt_token: str | None,
    syslog_host: str | None,
    syslog_port: int,
    syslog_protocol: str,
    snmp_host: str | None,
    snmp_port: int,
    netflow_host: str | None,
    netflow_port: int,
    netflow_version: str,
    http_url: str | None,
    kafka_brokers: str | None,
    kafka_topic_prefix: str,
    log_level: str,
    no_baseline: bool,
    dry_run: bool,
    snmp_state_path: str | None,
):
    """Network Log Generator — high-fidelity synthetic network data for Dynatrace."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Load topology
    logger.info(f"Loading topology from {config}")
    topology = load_topology(config)
    logger.info(f"Topology loaded: {len(topology.devices)} devices across "
                f"{len(set(d.site for d in topology.devices))} sites")

    # Initialize components
    rng = SeededRandom(seed)

    # Load scenario config from NETWORK_SCENARIO env var (matches epic's EPIC_SCENARIO pattern)
    scenario_config = None
    net_scenario = os.environ.get("NETWORK_SCENARIO")
    if net_scenario:
        # Try both underscore and hyphen variants of the name
        name_variants = [net_scenario, net_scenario.replace("_", "-"), net_scenario.replace("-", "_")]
        search_dirs = [
            Path(config).parent.parent / "scenarios",   # config/scenarios/ relative to topology
            Path("/app/config/scenarios"),                # container path
        ]
        for sdir in search_dirs:
            for variant in name_variants:
                sp = sdir / f"{variant}.json"
                if sp.is_file():
                    try:
                        import json as _json
                        scenario_config = _json.loads(sp.read_text())
                        logger.info("Loaded network scenario config: %s from %s", net_scenario, sp)
                    except Exception as exc:
                        logger.warning("Failed to load scenario config %s: %s", sp, exc)
                    break
            if scenario_config is not None:
                break
        if scenario_config is None:
            logger.warning("NETWORK_SCENARIO=%s set but no config file found", net_scenario)

    baseline = BaselineGenerator(topology, rng, scenario_config=scenario_config) if not no_baseline else None
    scenario_engine = ScenarioEngine(topology, rng)

    # Load scenario playbooks
    playbooks = []
    for s_path in scenario:
        pb = load_scenario(s_path)
        playbooks.append(pb)
        logger.info(f"Loaded scenario: {pb.name} ({len(pb.steps)} steps, {pb.duration_seconds}s)")

    # Run
    asyncio.run(_run(
        topology=topology,
        baseline=baseline,
        scenario_engine=scenario_engine,
        playbooks=playbooks,
        output_type=output,
        output_dir=output_dir,
        output_format=output_format,
        mode=mode,
        duration=duration,
        tick_interval=tick_interval,
        dt_endpoint=dt_endpoint,
        dt_token=dt_token,
        syslog_host=syslog_host,
        syslog_port=syslog_port,
        syslog_protocol=syslog_protocol,
        snmp_host=snmp_host,
        snmp_port=snmp_port,
        netflow_host=netflow_host,
        netflow_port=netflow_port,
        netflow_version=int(netflow_version),
        http_url=http_url,
        kafka_brokers=kafka_brokers,
        kafka_topic_prefix=kafka_topic_prefix,
        dry_run=dry_run,
        rng=rng,
        snmp_state_path=snmp_state_path,
    ))


async def _run(
    topology,
    baseline: BaselineGenerator | None,
    scenario_engine: ScenarioEngine,
    playbooks: list,
    output_type: str,
    output_dir: str,
    output_format: str,
    mode: str,
    duration: int,
    tick_interval: int,
    dt_endpoint: str | None,
    dt_token: str | None,
    syslog_host: str | None,
    syslog_port: int,
    syslog_protocol: str,
    snmp_host: str | None,
    snmp_port: int,
    netflow_host: str | None,
    netflow_port: int,
    netflow_version: int,
    http_url: str | None,
    kafka_brokers: str | None,
    kafka_topic_prefix: str,
    dry_run: bool,
    rng: SeededRandom,
    snmp_state_path: str | None = None,
):
    global _SHUTDOWN

    # Set up output adapters
    outputs: list[BaseOutput] = []
    use_all = output_type == "all"

    if output_type in ("file", "both") or use_all:
        outputs.append(FileOutput(output_dir=output_dir, format=output_format))
    if (output_type in ("dynatrace", "both") or use_all) and not dry_run:
        outputs.append(DynatraceOutput(endpoint=dt_endpoint, api_token=dt_token))
    if (output_type == "syslog" or use_all) and syslog_host:
        outputs.append(SyslogOutput(host=syslog_host, port=syslog_port, protocol=syslog_protocol))
    if (output_type == "snmp" or use_all) and snmp_host:
        outputs.append(SNMPTrapOutput(host=snmp_host, port=snmp_port))
    if (output_type == "netflow" or use_all) and netflow_host:
        outputs.append(NetFlowOutput(host=netflow_host, port=netflow_port, version=netflow_version))
    if (output_type == "http" or use_all) and http_url:
        outputs.append(HTTPWebhookOutput(url=http_url))
    if (output_type == "kafka" or use_all) and kafka_brokers:
        try:
            from netloggen.outputs.kafka_out import KafkaOutput
            outputs.append(KafkaOutput(bootstrap_servers=kafka_brokers, topic_prefix=kafka_topic_prefix))
        except ImportError:
            logger.warning("aiokafka not installed, skipping Kafka output")

    if dry_run and not outputs:
        outputs.append(FileOutput(output_dir=output_dir, format=output_format))

    for out in outputs:
        await out.connect()

    # Initialize clock
    start_time = datetime.now(timezone.utc)
    if mode == "batch":
        clock = Clock(mode=ClockMode.BATCH, start_time=start_time)
    else:
        clock = Clock(mode=ClockMode.REALTIME)

    # Stats counters
    stats = {"logs": 0, "metrics": 0, "traps": 0, "flows": 0, "ticks": 0}
    gen_start = time.monotonic()

    # Pre-generate all scenario events for batch mode
    scenario_events = {"logs": [], "metrics": [], "traps": [], "flows": []}
    for pb in playbooks:
        result = scenario_engine.execute_scenario(pb, start_time)
        for key in ("logs", "metrics", "traps", "flows"):
            scenario_events[key].extend(result.get(key, []))
        logger.info(f"Scenario '{pb.name}': generated {len(result['logs'])} logs, "
                    f"{len(result['metrics'])} metrics, {len(result['traps'])} traps")

    # Main generation loop
    tick_count = duration // tick_interval if mode == "batch" else 0
    current_tick = 0

    while not _SHUTDOWN:
        current_time = clock.now()

        # Baseline tick
        tick_data = {"logs": [], "metrics": [], "traps": [], "flows": []}
        if baseline:
            tick_data = baseline.generate_tick(current_time)

        # In batch mode, merge scenario events that fall within this tick window
        if mode == "batch":
            tick_start = current_tick * tick_interval
            tick_end = tick_start + tick_interval
            for key in ("logs", "metrics", "traps", "flows"):
                for evt in scenario_events[key]:
                    offset = (evt.timestamp - start_time).total_seconds()
                    if tick_start <= offset < tick_end:
                        tick_data[key].append(evt)

        # Dispatch to outputs
        for out in outputs:
            if tick_data["logs"]:
                sent = await out.send_logs(tick_data["logs"])
                stats["logs"] += sent
            if tick_data["metrics"]:
                sent = await out.send_metrics(tick_data["metrics"])
                stats["metrics"] += sent
            if tick_data["traps"]:
                sent = await out.send_traps(tick_data["traps"])
                stats["traps"] += sent
            if tick_data["flows"]:
                sent = await out.send_flows(tick_data["flows"])
                stats["flows"] += sent

        # Export state for SNMP agent (if enabled)
        if snmp_state_path and tick_data["metrics"]:
            from netloggen.snmpagent.state import export_device_state
            export_device_state(topology, tick_data["metrics"], snmp_state_path)

        stats["ticks"] += 1
        current_tick += 1

        # Advance clock
        if mode == "batch":
            clock.advance_batch(tick_interval)
            if current_tick >= tick_count:
                break
            # Progress reporting every 10 ticks
            if current_tick % 10 == 0:
                pct = (current_tick / tick_count) * 100
                logger.info(f"Progress: {pct:.0f}% ({current_tick}/{tick_count} ticks)")
        else:
            # Realtime mode — sleep between ticks
            await asyncio.sleep(tick_interval)

    # Cleanup
    elapsed = time.monotonic() - gen_start
    for out in outputs:
        await out.close()

    # Final report
    logger.info("=" * 60)
    logger.info("Generation complete!")
    logger.info(f"  Duration: {elapsed:.1f}s wall clock")
    logger.info(f"  Ticks:    {stats['ticks']}")
    logger.info(f"  Logs:     {stats['logs']:,}")
    logger.info(f"  Metrics:  {stats['metrics']:,}")
    logger.info(f"  Traps:    {stats['traps']:,}")
    logger.info(f"  Flows:    {stats['flows']:,}")
    logger.info(f"  Total:    {sum(v for k, v in stats.items() if k != 'ticks'):,} events")
    logger.info("=" * 60)


# ─── SNMP Agent Subcommand ────────────────────────────────────────

@cli.command("snmp-agent")
@click.option("--topology", "-t", type=click.Path(exists=True), required=True,
              help="Path to topology YAML (used for initial state if no state file exists yet).")
@click.option("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0).")
@click.option("--port", type=int, default=1161,
              help="UDP port to listen on (default: 1161; use 161 with root/capabilities).")
@click.option("--state-path", default="/tmp/netloggen-snmp-state.json",
              help="Path to shared state JSON file (written by generator).")
@click.option("--cache-ttl", type=float, default=5.0,
              help="Seconds to cache state before re-reading file (default: 5).")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), default="INFO")
def snmp_agent(
    topology: str,
    host: str,
    port: int,
    state_path: str,
    cache_ttl: float,
    log_level: str,
):
    """Run a standalone SNMP agent that responds to polls for simulated devices.

    Each device is addressable by using its hostname as the SNMP community string.
    The agent reads live state from the shared JSON file written by the generator.

    Example:
        netloggen snmp-agent --topology config/default-topology.yaml --port 1161

    Then poll a device:
        snmpwalk -v2c -c core-rtr-01 localhost:1161 1.3.6.1.2.1.1
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # If state file doesn't exist yet, bootstrap it from topology
    if not Path(state_path).exists():
        logger.info(f"No state file at {state_path}, bootstrapping from topology...")
        from netloggen.snmpagent.state import export_device_state
        topo = load_topology(topology)
        export_device_state(topo, [], state_path)
        logger.info(f"Bootstrapped state for {len(topo.devices)} devices")

    from netloggen.snmpagent.agent import run_agent
    logger.info(f"Starting SNMP agent on {host}:{port}")
    logger.info(f"Community string = device hostname (e.g., 'core-rtr-01')")

    try:
        asyncio.run(run_agent(host=host, port=port, state_path=state_path, cache_ttl=cache_ttl))
    except KeyboardInterrupt:
        logger.info("SNMP agent stopped")


@cli.command("snmp-poller")
@click.option("--state-path", default="/tmp/netloggen-snmp-state.json",
              help="Path to shared state JSON file (written by generator).")
@click.option("--dt-endpoint", envvar="DT_ENDPOINT",
              help="Dynatrace endpoint URL (or DT_ENDPOINT env var).")
@click.option("--dt-token", envvar="DT_API_TOKEN",
              help="Dynatrace API token (or DT_API_TOKEN env var).")
@click.option("--poll-interval", type=int, default=60,
              help="Seconds between poll cycles (default: 60).")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), default="INFO")
def snmp_poller(
    state_path: str,
    dt_endpoint: str,
    dt_token: str,
    poll_interval: int,
    log_level: str,
):
    """Poll SNMP device state and send metrics + logs to Dynatrace.

    Reads the shared state JSON file written by the generator's tick loop,
    converts device metrics (CPU, memory, interface counters) to MINT format,
    and sends them to Dynatrace Metrics API v2 and Log Ingest API.

    This emulates what a Dynatrace ActiveGate SNMP extension does:
    poll devices → convert to metrics → ingest into Dynatrace.

    Example:
        netloggen snmp-poller \\
            --state-path /tmp/netloggen-snmp-state.json \\
            --dt-endpoint https://<tenant>.dynatrace.com \\
            --dt-token $DT_API_TOKEN
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    if not dt_endpoint:
        click.echo("Error: --dt-endpoint or DT_ENDPOINT env var required.", err=True)
        sys.exit(1)
    if not dt_token:
        click.echo("Error: --dt-token or DT_API_TOKEN env var required.", err=True)
        sys.exit(1)

    from netloggen.snmppoller.poller import run_poller
    try:
        asyncio.run(run_poller(
            state_path=state_path,
            dt_endpoint=dt_endpoint,
            dt_token=dt_token,
            poll_interval=poll_interval,
        ))
    except KeyboardInterrupt:
        logger.info("SNMP poller stopped")


@cli.command("web-ui")
@click.option("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1).")
@click.option("--port", type=int, default=8088, help="HTTP port (default: 8088).")
@click.option("--flags-path", default="/tmp/netloggen-flags.json",
              help="Path to feature flags JSON file.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), default="INFO")
def web_ui(host: str, port: int, flags_path: str, log_level: str):
    """Run the feature flags web UI.

    Provides a browser-based control panel for toggling generator scenarios
    and managing systemd services (start/stop/restart).

    Example:
        netloggen web-ui --host 0.0.0.0 --port 8088
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    from netloggen.webui.server import run_webui
    run_webui(host=host, port=port, flags_path=flags_path)


# ─── Backward compatibility: `main` entry point ──────────────────

def main():
    """Entry point for `netloggen` console script.

    Supports both new-style subcommands (`netloggen generate`, `netloggen snmp-agent`)
    and legacy invocation (`netloggen --config ...` which maps to `generate`).
    """
    # If first arg looks like an option (starts with -), assume legacy `generate` invocation
    import sys as _sys
    args = _sys.argv[1:]
    if args and args[0].startswith("-"):
        generate(standalone_mode=True)
    else:
        cli()


if __name__ == "__main__":
    cli()
