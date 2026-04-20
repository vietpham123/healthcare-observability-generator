# Dynatrace Assets

Exportable configuration JSONs for all Dynatrace components used by the Healthcare Observability Generator.

## Files

| File | Schema | Description |
|------|--------|-------------|
| `anomaly-detectors.json` | `builtin:davis.anomaly-detectors` | 6 Davis Anomaly Detection app alerts (DQL-based, Grail) |
| `openpipeline-healthcare.json` | `builtin:openpipeline.logs.pipelines` | 2 OpenPipeline configs (Epic + Network) with processors and routing |
| `log-event-alerts-classic.json` | `builtin:logmonitoring.log-events` | **DEPRECATED** — classic log event alerts, replaced by anomaly-detectors.json |
| `metric-event-alerts-classic.json` | `builtin:anomaly-detection.metric-events` | **DEPRECATED** — classic metric event alert, replaced by anomaly-detectors.json |

## Importing

### Anomaly Detectors (Recommended)

Use the Settings 2.0 API via the **platform endpoint**:

```bash
curl 'https://{env-id}.apps.dynatrace.com/platform/classic/environment-api/v2/settings/objects' \
  -X POST \
  -H 'Authorization: Bearer {platform-token}' \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d @anomaly-detectors.json
```

Required permissions:
- `settings:schemas:read`, `settings:objects:read`, `settings:objects:write`
- `storage:logs:read`, `storage:metrics:read`, `storage:buckets:read`
- `davis:analyzers:execute` (if not using service user)

### OpenPipeline

Import via the classic Settings 2.0 API:

```bash
curl 'https://{env-id}.dynatrace.com/api/v2/settings/objects' \
  -X POST \
  -H 'Authorization: Api-Token {api-token}' \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d @openpipeline-healthcare.json
```

## Alert → Scenario Cross-Reference

| Scenario | Alerts That Fire |
|----------|-----------------|
| Normal Day Shift | None (baseline) |
| Ransomware Attack | Failed Login Burst + Firewall Threat Burst |
| Insider Threat Snooping | Break-the-Glass Activity Spike |
| HL7 Interface Failure | HL7 Message Delivery Failure + Mirth Queue Backup |
| Core Switch Failure | Network Interface Errors |

## Analyzer Models Used

| Alert | Model | Rationale |
|-------|-------|-----------|
| Failed Login Burst | Auto-Adaptive | Variable baseline, learns normal login failure rate |
| Firewall Threat Burst | Auto-Adaptive | Variable baseline, learns normal threat event rate |
| Break-the-Glass | Static (>3/min) | Rare events — any burst is significant |
| Network Interface Errors | Static (>1/min) | Should be zero during normal operations |
| HL7 Delivery Failure | Static (>2/min) | Should be zero during normal operations |
| Mirth Queue Backup | Static (>50 depth) | Clear operational threshold |
