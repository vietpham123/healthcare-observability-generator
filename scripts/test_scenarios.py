#!/usr/bin/env python3
"""Comprehensive scenario test — validates scenario activation, ConfigMap patching,
generator env-var pickup, and deactivation/normalization across all 5 scenarios.

Validates via:
  - WebUI API response codes and payloads
  - AKS ConfigMap values (via SSH + kubectl)
  - Generator pod logs (startup lines, anomaly markers, overrides)
  - Pod health (Running state)

Note: Epic generator events are sent to DT via OTLP, NOT to stdout.
      Only startup lines, [anomaly], [override], and [tick N] appear in kubectl logs.
      Network generator uses Python logging to stderr (captured by kubectl logs).
"""

import subprocess, json, time, sys, re
from datetime import datetime

WEBUI = "http://172.206.131.122"
SSH = "ssh -i ~/.ssh/VPET_key.pem azureuser@52.248.43.42"
NS = "healthcare-gen"

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"

results = []


def run(cmd, timeout=30):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()


def ssh(cmd, timeout=30):
    return run(f'{SSH} "{cmd}"', timeout=timeout)


def curl_json(url, method="GET"):
    flag = "-X POST" if method == "POST" else ""
    raw = run(f'curl -s {flag} {url}')
    try:
        return json.loads(raw)
    except Exception:
        return {"error": raw}


def kube_logs(deploy, lines=200, since="120s"):
    return ssh(f"kubectl -n {NS} logs deploy/{deploy} --tail={lines} --since={since}")


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((label, condition, detail))
    print(f"  {status}  {label}" + (f"  ({detail})" if detail else ""), flush=True)
    return condition


def activate(key):
    print(f"\n>>> Activating: {key}", flush=True)
    d = curl_json(f"{WEBUI}/api/scenarios/{key}/activate", "POST")
    status = d.get("status", "error")
    epic = d.get("epic_scenario", "?")
    net_restarted = d.get("network_restarted", False)
    cm = d.get("configmap_patched", False)
    print(f"    status={status}  epic_scenario={epic}  cm_patched={cm}  net_restarted={net_restarted}", flush=True)
    return d


def deactivate_all():
    print("\n>>> Deactivating all", flush=True)
    d = curl_json(f"{WEBUI}/api/scenarios/deactivate-all", "POST")
    print(f"    status={d.get('status', '?')}", flush=True)
    return d


def wait(secs, msg="data"):
    print(f"    Waiting {secs}s for {msg}...", flush=True)
    time.sleep(secs)


def pods_running():
    out = ssh(f"kubectl -n {NS} get pods --no-headers")
    lines = [l for l in out.split("\n") if l.strip()]
    running = [l for l in lines if "Running" in l]
    return len(running), len(lines)


def get_configmap():
    """Return (EPIC_SCENARIO, NETWORK_SCENARIO) from the live ConfigMap."""
    epic = ssh(f"kubectl -n {NS} get configmap generator-config -o jsonpath='{{.data.EPIC_SCENARIO}}'")
    net = ssh(f"kubectl -n {NS} get configmap generator-config -o jsonpath='{{.data.NETWORK_SCENARIO}}'")
    return epic, net


# ── Scenario-specific log pattern checks ──────────────────────────

def check_epic_logs(scenario_label, epic_key, expect_anomaly=False, expect_overrides=None):
    """Check epic-generator logs for startup, anomaly markers, and overrides."""
    logs = kube_logs("epic-generator", lines=200, since="120s")
    if not logs:
        check(f"[Epic] Logs available ({scenario_label})", False, "no logs")
        return

    lines = logs.splitlines()
    check(f"[Epic] Logs available ({scenario_label})", len(lines) >= 2, f"{len(lines)} lines")

    # Startup line always present
    check(f"[Epic] Generator started", "Epic SIEM Generator starting" in logs)

    # DT output enabled
    check(f"[Epic] DT output enabled", "Dynatrace output enabled" in logs)

    # Mirth emitter enabled
    check(f"[Epic] Mirth emitter enabled", "Mirth metrics emitter enabled" in logs)

    if expect_anomaly:
        check(f"[Epic] Anomaly active ({epic_key})",
              f"[anomaly] ACTIVE: type={epic_key}" in logs)
    else:
        check(f"[Epic] No anomaly (baseline)",
              "[anomaly] ACTIVE" not in logs)

    if expect_overrides:
        for pat, desc in expect_overrides:
            check(f"[Epic] {desc}", pat in logs)


def check_network_logs(scenario_label, scenario_key, expect_scenario_found=True,
                       expect_device_down=None, expect_cpu_spike=None):
    """Check network-generator logs for topology load, scenario config, device events."""
    logs = kube_logs("network-generator", lines=200, since="120s")
    if not logs:
        check(f"[Network] Logs available ({scenario_label})", False, "no logs")
        return

    lines = logs.splitlines()
    check(f"[Network] Logs available ({scenario_label})", len(lines) >= 2, f"{len(lines)} lines")

    # Topology always loads
    check(f"[Network] Topology loaded", "Topology loaded:" in logs)

    # DT output connected
    check(f"[Network] DT output connected", "Dynatrace output connected" in logs)

    if scenario_key and expect_scenario_found:
        check(f"[Network] Scenario config loaded",
              f"Loaded network scenario config: {scenario_key}" in logs)
        check(f"[Network] No config-not-found warning",
              "no config file found" not in logs.lower())
    elif scenario_key and not expect_scenario_found:
        check(f"[Network] Scenario config NOT found (expected)",
              "no config file found" in logs.lower())

    if expect_device_down:
        for device in expect_device_down:
            check(f"[Network] Device {device} DOWN",
                  f"device {device} marked DOWN" in logs)

    if expect_cpu_spike:
        for device in expect_cpu_spike:
            check(f"[Network] Device {device} CPU spike",
                  f"device {device} CPU spike" in logs)


# ============================================================
print("=" * 60, flush=True)
print("  HEALTHCARE SCENARIO COMPREHENSIVE TEST", flush=True)
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
print("=" * 60, flush=True)

# ── PRE-FLIGHT ────────────────────────────────────────────────────

print("\n--- PRE-FLIGHT CHECKS ---", flush=True)
status = curl_json(f"{WEBUI}/api/status")
check("[WebUI] /api/status responds", "scenarios" in status)
check("[WebUI] k8s connected", status.get("k8s_connected") is True)
scenarios = status.get("scenarios", [])
check("[WebUI] 5 scenarios listed", len(scenarios) == 5, f"got {len(scenarios)}")

scenario_keys = {s["key"] for s in scenarios}
for expected in ["normal-day-shift", "core-switch-failure", "hl7-interface-failure",
                 "insider-threat-snooping", "ransomware-attack"]:
    check(f"[WebUI] Scenario '{expected}' exists", expected in scenario_keys)

# Ensure clean state
deactivate_all()
wait(15, "clean slate + pod restart")

r, t = pods_running()
check("[Infra] All pods running after deactivate-all", r == t, f"{r}/{t}")

# Verify deactivation reset ConfigMap
epic_cm, net_cm = get_configmap()
check("[ConfigMap] EPIC_SCENARIO=normal_shift after deactivate-all", epic_cm == "normal_shift", epic_cm)
check("[ConfigMap] NETWORK_SCENARIO='' after deactivate-all", net_cm == "", f"'{net_cm}'")


# ============================================================
# TEST 1: NORMAL DAY SHIFT (Baseline / Normalize)
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST 1: NORMAL DAY SHIFT (Baseline)", flush=True)
print("=" * 60, flush=True)

d = activate("normal-day-shift")
check("[Activate] normal-day-shift succeeded", d.get("status") == "activated")
check("[Activate] epic_scenario=normal_shift", d.get("epic_scenario") == "normal_shift")
check("[Activate] configmap_patched", d.get("configmap_patched") is True)

# Verify ConfigMap
epic_cm, net_cm = get_configmap()
check("[ConfigMap] EPIC_SCENARIO=normal_shift", epic_cm == "normal_shift", epic_cm)
check("[ConfigMap] NETWORK_SCENARIO=normal-day-shift", net_cm == "normal-day-shift", f"'{net_cm}'")

wait(30, "pod restart + startup")

r, t = pods_running()
check("[Infra] Pods running after baseline", r == t, f"{r}/{t}")

check_epic_logs("baseline", "normal_shift",
    expect_anomaly=False)

check_network_logs("baseline", "normal-day-shift",
    expect_scenario_found=True)  # found but no events = pure baseline


# ============================================================
# TEST 2: CORE SWITCH FAILURE
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST 2: CORE SWITCH FAILURE", flush=True)
print("=" * 60, flush=True)

d = activate("core-switch-failure")
check("[Activate] core-switch-failure succeeded", d.get("status") == "activated")
check("[Activate] epic_scenario=core_switch_failure", d.get("epic_scenario") == "core_switch_failure")

epic_cm, net_cm = get_configmap()
check("[ConfigMap] EPIC_SCENARIO=core_switch_failure", epic_cm == "core_switch_failure", epic_cm)
check("[ConfigMap] NETWORK_SCENARIO=core-switch-failure", net_cm == "core-switch-failure", f"'{net_cm}'")

wait(30, "pod restart + startup")

r, t = pods_running()
check("[Infra] Pods running", r == t, f"{r}/{t}")

check_epic_logs("core-switch-failure", "core_switch_failure",
    expect_anomaly=True,
    expect_overrides=[
        ("[override] FHIR error_bias=0.4", "FHIR error_bias override"),
        ("[override] ETL failure_bias=0.5", "ETL failure_bias override"),
        ("[override] HL7 generation disabled", "HL7 disabled override"),
    ])

check_network_logs("core-switch-failure", "core-switch-failure",
    expect_scenario_found=True,
    expect_device_down=["kcrmc-core-01"],
    expect_cpu_spike=["kcrmc-dist-epic-01", "kcrmc-dist-epic-02"])

# Deactivate and verify reset
deactivate_all()
epic_cm, net_cm = get_configmap()
check("[Deactivate] EPIC reset to normal_shift", epic_cm == "normal_shift", epic_cm)
check("[Deactivate] NETWORK cleared", net_cm == "", f"'{net_cm}'")

wait(20, "recovery")


# ============================================================
# TEST 3: HL7 INTERFACE FAILURE
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST 3: HL7 INTERFACE FAILURE", flush=True)
print("=" * 60, flush=True)

d = activate("hl7-interface-failure")
check("[Activate] hl7-interface-failure succeeded", d.get("status") == "activated")
check("[Activate] epic_scenario=hl7_interface_failure", d.get("epic_scenario") == "hl7_interface_failure")

epic_cm, net_cm = get_configmap()
check("[ConfigMap] EPIC_SCENARIO=hl7_interface_failure", epic_cm == "hl7_interface_failure", epic_cm)
check("[ConfigMap] NETWORK_SCENARIO=hl7-interface-failure", net_cm == "hl7-interface-failure", f"'{net_cm}'")

wait(30, "pod restart + startup")

r, t = pods_running()
check("[Infra] Pods running", r == t, f"{r}/{t}")

check_epic_logs("hl7-interface-failure", "hl7_interface_failure",
    expect_anomaly=True,
    expect_overrides=[
        ("[override] FHIR error_bias=0.65", "FHIR error_bias=0.65 override"),
        ("[override] ETL failure_bias=0.7", "ETL failure_bias=0.7 override"),
        ("[override] HL7 generation disabled", "HL7 disabled override"),
    ])

check_network_logs("hl7-interface-failure", "hl7-interface-failure",
    expect_scenario_found=True)
# HL7 interface failure uses interface_errors and port_flap, not device_down

# Deactivate and verify
deactivate_all()
epic_cm, net_cm = get_configmap()
check("[Deactivate] EPIC reset to normal_shift", epic_cm == "normal_shift", epic_cm)
check("[Deactivate] NETWORK cleared", net_cm == "", f"'{net_cm}'")

wait(20, "recovery")


# ============================================================
# TEST 4: INSIDER THREAT
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST 4: INSIDER THREAT (Epic-only, no network correlation)", flush=True)
print("=" * 60, flush=True)

d = activate("insider-threat-snooping")
check("[Activate] insider-threat succeeded", d.get("status") == "activated")
check("[Activate] epic_scenario=insider_threat", d.get("epic_scenario") == "insider_threat")

epic_cm, net_cm = get_configmap()
check("[ConfigMap] EPIC_SCENARIO=insider_threat", epic_cm == "insider_threat", epic_cm)
check("[ConfigMap] NETWORK_SCENARIO=insider-threat-snooping", net_cm == "insider-threat-snooping", f"'{net_cm}'")

wait(30, "pod restart + startup")

r, t = pods_running()
check("[Infra] Pods running", r == t, f"{r}/{t}")

check_epic_logs("insider-threat", "insider_threat",
    expect_anomaly=True)
# Insider threat has no generator_overrides

check_network_logs("insider-threat", "insider-threat-snooping",
    expect_scenario_found=True)
# network_correlation.enabled=False → scenario file found but no device events applied

# Deactivate and verify
deactivate_all()
epic_cm, net_cm = get_configmap()
check("[Deactivate] EPIC reset to normal_shift", epic_cm == "normal_shift", epic_cm)
check("[Deactivate] NETWORK cleared", net_cm == "", f"'{net_cm}'")

wait(20, "recovery")


# ============================================================
# TEST 5: RANSOMWARE ATTACK
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST 5: RANSOMWARE ATTACK", flush=True)
print("=" * 60, flush=True)

d = activate("ransomware-attack")
check("[Activate] ransomware-attack succeeded", d.get("status") == "activated")
check("[Activate] epic_scenario=ransomware", d.get("epic_scenario") == "ransomware")

epic_cm, net_cm = get_configmap()
check("[ConfigMap] EPIC_SCENARIO=ransomware", epic_cm == "ransomware", epic_cm)
check("[ConfigMap] NETWORK_SCENARIO=ransomware-attack", net_cm == "ransomware-attack", f"'{net_cm}'")

wait(30, "pod restart + startup")

r, t = pods_running()
check("[Infra] Pods running", r == t, f"{r}/{t}")

check_epic_logs("ransomware", "ransomware",
    expect_anomaly=True,
    expect_overrides=[
        ("[override] FHIR error_bias=0.3", "FHIR error_bias=0.3 override"),
        ("[override] ETL failure_bias=0.4", "ETL failure_bias=0.4 override"),
    ])

check_network_logs("ransomware", "ransomware-attack",
    expect_scenario_found=True)
# Ransomware network events are UTM/threat type, not device_down


# ============================================================
# TEST 6: DEACTIVATE SINGLE SCENARIO
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST 6: DEACTIVATE SINGLE SCENARIO", flush=True)
print("=" * 60, flush=True)

# ransomware-attack should still be active from TEST 5
d = curl_json(f"{WEBUI}/api/scenarios/ransomware-attack/deactivate", "POST")
check("[Deactivate] ransomware-attack single", d.get("status") == "deactivated")
check("[Deactivate] configmap_patched", d.get("configmap_patched") is True)

epic_cm, net_cm = get_configmap()
check("[Deactivate] EPIC reset to normal_shift", epic_cm == "normal_shift", epic_cm)
check("[Deactivate] NETWORK cleared", net_cm == "", f"'{net_cm}'")

wait(20, "pod restart")

r, t = pods_running()
check("[Infra] Pods running after single deactivate", r == t, f"{r}/{t}")


# ============================================================
# TEST 7: NORMALIZE VIA NORMAL-DAY-SHIFT (vs deactivate-all)
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST 7: NORMALIZE VIA ACTIVATING NORMAL-DAY-SHIFT", flush=True)
print("=" * 60, flush=True)

# First activate a failure scenario
activate("core-switch-failure")
wait(10, "scenario activation")

epic_cm, net_cm = get_configmap()
check("[Pre-normalize] EPIC=core_switch_failure", epic_cm == "core_switch_failure", epic_cm)

# Now normalize by clicking normal-day-shift
d = activate("normal-day-shift")
check("[Normalize] normal-day-shift succeeded", d.get("status") == "activated")

epic_cm, net_cm = get_configmap()
check("[Normalize] EPIC reset to normal_shift", epic_cm == "normal_shift", epic_cm)
check("[Normalize] NETWORK=normal-day-shift", net_cm == "normal-day-shift", f"'{net_cm}'")

wait(30, "pod restart")

r, t = pods_running()
check("[Infra] Pods running after normalize", r == t, f"{r}/{t}")

check_epic_logs("normalize", "normal_shift", expect_anomaly=False)
check_network_logs("normalize", "normal-day-shift", expect_scenario_found=True)


# ============================================================
# CLEANUP
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  CLEANUP", flush=True)
print("=" * 60, flush=True)

deactivate_all()
activate("normal-day-shift")
wait(15, "final baseline")

r, t = pods_running()
check("[Final] All pods running", r == t, f"{r}/{t}")

status = curl_json(f"{WEBUI}/api/status")
active = [s for s in status.get("scenarios", []) if s.get("active")]
check("[Final] Only normal-day-shift active",
      len(active) == 1 and active[0]["key"] == "normal-day-shift")


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60, flush=True)
print("  TEST SUMMARY", flush=True)
print("=" * 60, flush=True)

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)

print(f"\n  Total: {total}  |  {PASS}: {passed}  |  {FAIL}: {failed}", flush=True)

if failed > 0:
    print(f"\n  Failed checks:", flush=True)
    for label, ok, detail in results:
        if not ok:
            print(f"    {FAIL}  {label}" + (f"  ({detail})" if detail else ""), flush=True)

print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
print("=" * 60, flush=True)

sys.exit(0 if failed == 0 else 1)
