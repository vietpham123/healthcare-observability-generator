# Scenario Test Report — v2.3.0

**Date:** 2026-04-20
**Version:** v2.3.0 (4-scenario consolidation + Mirth Connect)

## Summary

Consolidated from 8 scenarios to 4 focused scenarios. Each scenario now turns a distinct
DT app page RED, eliminating overlap and broken mappings. Added Mirth Connect integration
engine metrics emitter.

## Scenario Results

### 1. Ransomware Attack ✅
- **Activation:** `POST /api/scenarios/ransomware-attack/activate`
- **Epic key:** `ransomware`
- **Impact:** Auth page RED — login failures spike (Epic indicators #1, #2)
- **Mechanism:** 4-phase anomaly (Recon → Harvest → Lateral → Exfil), 15 events/tick
- **Mirth:** Baseline (no impact on integration engine)
- **Recovery:** Deactivate → normal_shift → ~5 min

### 2. Insider Threat ✅
- **Activation:** `POST /api/scenarios/insider-threat-snooping/activate`
- **Epic key:** `insider_threat`
- **Impact:** Security page RED — BTG count spikes (indicator #3)
- **Mechanism:** Event sequence (HKU_LOGIN → SEARCH → BTG → CHART_ACCESS), 4 events/tick
- **Mirth:** Baseline
- **Recovery:** Deactivate → normal_shift → ~5 min

### 3. HL7 Interface Failure ✅ (NEW)
- **Activation:** `POST /api/scenarios/hl7-interface-failure/activate`
- **Epic key:** `hl7_interface_failure`
- **Impact:** Integration page RED — FHIR errors ≥50%, ETL failures ≥70%, Mirth queue backup
- **Mechanism:**
  - `generator_overrides.fhir_error_bias=0.65` forces 65% FHIR 5xx responses
  - `generator_overrides.etl_failure_bias=0.70` forces 70% ETL FAILED/TIMEOUT
  - `generator_overrides.hl7_disabled=true` stops HL7 message generation
  - `generator_overrides.mirth_scenario=hl7_interface_failure` escalates Mirth queue depth
- **Mirth:** Queue depth climbs from 0→5000 over 60 ticks, HL7v2 channels stop sending
- **Recovery:** Deactivate → normal_shift → ~3 min (queue drains)

### 4. Core Switch Failure ✅ (NEW)
- **Activation:** `POST /api/scenarios/core-switch-failure/activate`
- **Epic key:** `core_switch_failure`
- **Impact:** Network page RED — device up ratio drops, CPU spikes on surviving switches
- **Mechanism:**
  - Mild `fhir_error_bias=0.15` and `etl_failure_bias=0.20` for intermittent connectivity
  - `mirth_scenario=core_switch_failure` adds 30% degradation to Mirth metrics
  - Primary impact is on network generator (devices going offline)
- **Recovery:** Deactivate → normal_shift → ~5 min

## Retired Scenarios

The following scenarios were removed in v2.3.0 due to overlap or broken mappings:

| Scenario | Reason |
|----------|--------|
| ED Surge | Barely visible — volume increase but ratios unchanged |
| MyChart Credential Stuffing | Mapped to mychart_peak (normal activity, not attack) |
| Brute Force | Overlapped with Ransomware (same login failure signal) |
| HIPAA Audit | Low usage, audit-only scenario |
| Privacy Breach | Overlapped with Insider Threat (same BTG signal) |
| IoMT Device Compromise | Network-only, mapped to normal_shift (no Epic impact) |
| Epic Outage Network Root Cause | Network-only, mapped to normal_shift |

## DT App Health Indicators

| # | Indicator | Page | Green | Amber | Scenario Impact |
|---|-----------|------|-------|-------|-----------------|
| 1 | Epic Login Success % | Epic, Security | ≥65% | ≥45% | Ransomware: RED |
| 2 | Auth Login Success % | Auth, Security | ≥80% | ≥60% | Ransomware: RED |
| 3 | BTG Count | Security | ≤200 | ≤400 | Insider Threat: RED |
| 4 | FHIR Health % | Integration | ≥85% | ≥70% | HL7 Failure: RED |
| 5 | ETL Success % | Integration | ≥88% | ≥70% | HL7 Failure: RED |
| 6 | HL7 Delivery Rate | Integration | ≥99% | ≥50% | HL7 Failure: RED |
| 7 | MyChart Login % | MyChart | ≥95% | ≥80% | — |
| 8 | STAT Order Rate | Epic | ≤5% | ≤10% | — |
| 9 | Avg Device CPU | Network | ≤40% | ≤60% | Core Switch: RED |
| 10 | Device Up Ratio | Network | 100% | ≥95% | Core Switch: RED |
| 11 | Mirth Channel Health | Integration | 100% | ≥80% | HL7 Failure: RED (NEW) |

## Container Versions

| Image | Tag |
|-------|-----|
| healthcare-gen/epic | v1.0.5 |
| healthcare-gen/webui | v2.3.0 |
| healthcare-gen/network | latest |
| DT App | v1.15.0 |
