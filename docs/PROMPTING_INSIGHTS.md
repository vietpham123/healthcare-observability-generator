# Prompting Insights — AI-Assisted Development Analysis

## Executive Summary

This document captures patterns, lessons, and insights from building the Healthcare Observability Generator through iterative AI-assisted development across multiple sessions. The project evolved from a standalone Epic SIEM log generator into a multi-domain healthcare observability platform with Kubernetes deployment, Dynatrace app integration, and OpenPipeline processing — all directed through conversational prompting.

---

## Project Trajectory

### Session Map

| Session | Focus | Complexity | Key Outcome |
|---------|-------|------------|-------------|
| 1 | Epic SIEM generator foundation | Low | Monolithic generator, file output |
| 2 | Generator expansion | Medium | +5 log types (Clinical, HL7, FHIR, MyChart, ETL) |
| 3 | Transport & scheduling | Medium | +5 output modes, time-of-day curves, scenarios |
| 4 | Network generator | High | 12 vendor emulators, SNMP, NetFlow, topology engine |
| 5 | Consolidation + AKS deploy | High | Combined repo, Docker builds, K8s manifests, DT operator |
| 6 | Dynatrace app + OpenPipeline | Very High | 8-page DT Platform App, custom OpenPipeline, gap analysis |
| 7 | Fidelity gap repair | Very High | 30+ mnemonic fields, login events, service audit, auth page |
| 8 | Documentation + repo hygiene | Medium | Docs, prompt analysis, sanitization review |
| 9 | Documentation + scenario testing | Very High | Comprehensive 8-scenario validation, baseline recovery tracking, recovery-time discovery |

### Complexity Curve

Sessions 1-3 were additive (build more generators). Session 4 was a lateral expansion (network domain). Sessions 5+ introduced integration complexity (K8s + DT APIs + app development + OpenPipeline), where each change affected multiple systems simultaneously.

---

## Effective Prompting Patterns

### 1. Specification-First Prompting

**Pattern:** Front-load the request with explicit tables, field lists, or schemas before asking for code.

**Example:** Providing a table of all 13 SIEM mnemonic categories with expected field names, fidelity scores, and gap descriptions before requesting generator fixes.

**Why it works:** The agent receives structured requirements it can validate against, rather than inferring intent from prose. Reduces back-and-forth clarification cycles.

**Observed success rate:** ~90% — specification-first prompts produced working code on the first attempt in most cases.

### 2. Domain Anchoring

**Pattern:** Use domain-specific terminology from the target system (Epic, HL7, FHIR, Cisco IOS) to constrain generation.

**Example:** "Generate HL7v2 ADT^A01 messages with PID, PV1, and NK1 segments using pipe delimiters" vs. "Generate hospital messages."

**Why it works:** Domain terms act as implicit constraints. The agent's training data contains real examples of these formats, so domain-anchored prompts produce output that matches real-world expectations.

**Risk:** If the domain term is ambiguous (e.g., "mnemonic" means different things in Epic vs. general usage), the agent may generate plausible-but-wrong output. Always verify against real examples.

### 3. Progressive Disclosure

**Pattern:** Start with high-level intent, let the agent propose an approach, then refine with specific corrections.

**Example flow:**
1. "Add login events to the Epic generator" (intent)
2. Agent proposes approach
3. "Use BCA_LOGIN_SUCCESS and FAILEDLOGIN as the E1Mid values, include CLIENT_TYPE and LOGINERROR in the mnemonics" (refinement)
4. Agent produces specific code
5. "The flag value should be Access History^^ not Workflow Logging" (correction)

**Why it works:** Each prompt narrows the solution space while allowing the agent to contribute structural decisions. Avoids the overhead of specifying every detail upfront (which works for specs, but not for novel architecture decisions).

### 4. Fix-Forward with Diagnostics

**Pattern:** When something fails, include the full error output and the command that produced it, then ask for a fix.

**Example:** Pasting the HTTP 405 error from the OpenPipeline API update, along with the curl command used, and asking "fix this."

**Why it works:** The agent can pattern-match the error to known causes (405 = wrong HTTP method) without needing to reason about the full system state. Including the command prevents the agent from suggesting the same broken approach.

**Anti-pattern:** Saying "it didn't work" without the error output. This forces the agent to guess, which often produces a different-but-also-wrong approach.

### 5. Standing Instructions

**Pattern:** Set persistent rules at the start of a session that apply to all subsequent actions.

**Examples used in this project:**
- "Send a ntfy notification if you get stuck"
- "Always verify by querying DT after any deploy"
- "Use the operator token for Settings API, platform token for DQL"

**Why it works:** Reduces repetition and ensures the agent doesn't forget operational constraints. Standing instructions create a "session protocol" that the agent follows without re-prompting.

### 6. Compound Task with Approval Gate

**Pattern:** Request multiple related actions but insert a checkpoint before the irreversible ones.

**Example:** "Update OpenPipeline to extract new fields, verify they appear in DQL, then add panels to the DT app — but show me the query results before deploying the app."

**Why it works:** Allows the agent to batch preparatory work (faster) while giving the user control over the high-risk step (deploy). The agent can parallelize the first two tasks, pause for approval, then proceed.

---

## Anti-Patterns Observed

### 1. Assuming Attribute Names

**Problem:** The agent assumed `event.type` was the correct attribute name when the actual OpenPipeline output used `E1Mid`.

**Lesson:** Always verify field names by querying actual data before building queries or panels. Never trust assumed attribute names — run a `| fields *` query first.

### 2. Indentation Drift in Multi-Step Edits

**Problem:** When making sequential file edits, the agent occasionally mismatched indentation in Python files, especially when inserting new code blocks adjacent to existing ones.

**Lesson:** For large code changes, prefer replacing entire methods or blocks rather than inserting fragments. Provide clear context boundaries.

### 3. API Method Guessing

**Problem:** The agent used HTTP PUT for OpenPipeline updates when the Settings API v2 requires POST for upsert operations. Also tried `queryExecute` before learning the correct query path.

**Lesson:** API behaviors aren't always predictable from conventions. When working with unfamiliar APIs, test a minimal request first before building complex payloads.

### 4. Deploy Before Test

**Problem:** Early sessions sometimes deployed code changes without verifying they produced correct output locally.

**Lesson:** Always run a validation step (query DT, check pod logs, verify field extraction) between "apply change" and "deploy to production."

---

## Prompt Architecture Insights

### Context Stack

Effective prompts for this project followed a consistent structure:

```
[Standing Instructions]          ← Session-wide rules (ntfy, tokens, repo)
  [Current State]                ← What's deployed, what's working
    [Diagnostic Data]            ← Error output, query results, field lists
      [Specific Request]         ← What to do next
        [Success Criteria]       ← How to verify it worked
```

The most productive prompts included at least 3 of these 5 layers.

### Verification Loop

The most reliable workflow was:

```
Change → Deploy → Query → Verify → Next
```

Skipping "Query" or "Verify" always led to wasted iterations. The DQL query endpoint was the single most valuable verification tool — every change could be validated by running a 2-line query within 30 seconds.

### Escalation Ladder

When the agent got stuck, the most effective escalation was:

1. Provide the exact error message (80% of issues resolved here)
2. Provide a working example of the desired output format (15%)
3. Break the task into smaller steps with individual verification (4%)
4. Manual intervention (1%)

---

## Quantitative Observations

### Prompt-to-Outcome Ratios

| Task Type | Avg Prompts | Avg Iterations | Notes |
|-----------|-------------|----------------|-------|
| New generator file | 1-2 | 1 | Specification-first works well |
| Bug fix (with error) | 1 | 1 | Fix-forward is efficient |
| DT app page creation | 2-3 | 1-2 | Component API discovery adds a round |
| OpenPipeline config | 3-5 | 2-3 | API method + field name verification |
| K8s deployment | 2-4 | 1-2 | YAML generation is reliable, debugging less so |
| Cross-system correlation | 4-6 | 2-3 | Generator + Pipeline + App changes chain |

### Error Categories

| Category | Frequency | Impact | Mitigation |
|----------|-----------|--------|------------|
| Wrong API method | 15% | Medium | Test minimal call first |
| Wrong attribute name | 20% | High | Query actual data before building on assumptions |
| Syntax/indentation | 10% | Low | Replace whole blocks, not fragments |
| Missing import | 5% | Low | Usually caught by type checker |
| Logic error | 10% | Medium | Verify with real data queries |
| Correct on first try | 40% | — | Specification-first + domain anchoring |

---

## Recommendations for Future Sessions

1. **Start with a state summary** — Tell the agent what's deployed, what version, what's working. Saves 2-3 diagnostic prompts.
2. **Use structured specs** — Tables > prose for field lists, API contracts, and data schemas.
3. **Verify after every deploy** — Run a DQL query or API call to confirm. Never stack multiple unverified changes.
4. **Set standing instructions early** — Token assignments, repo paths, notification channels.
5. **Commit the verification queries** — The DQL queries used for testing are valuable documentation. Keep them.
6. **Separate concerns per prompt** — "Fix the generator AND update the app AND modify OpenPipeline" works poorly. "Fix the generator, verify, then update the app" works well.
7. **Include the wrong repo path explicitly** — This project hit a repo-confusion bug. Always state the exact file paths for multi-repo projects.


---

## Session 9 Insights — Scenario Testing & Documentation

### New Prompting Pattern: Automated Verification Loop

**Pattern**: Issue a single "test all scenarios" directive and let the agent execute an automated test loop with standardized verification at each step.

**Flow**:
```
Activate scenario → Wait 60-90s → Query DQL health indicators → Record results → Deactivate → Wait for recovery → Repeat
```

**Why it works**: The agent can execute a consistent verification protocol across all 8 scenarios without human intervention. Each scenario gets the same battery of health indicator queries, producing comparable results.

**Challenge**: Long wait times (60-90s per scenario for data to flow, plus recovery time) make this a wall-clock-intensive operation. The agent must be patient and not skip wait steps.

### New Anti-Pattern: Cascading Test Contamination

**Problem**: Testing the ransomware scenario (which generates ~1450 failed logins) contaminated the 30-minute DQL query window. Every subsequent scenario test showed RED health indicators even though the new scenario was not the cause.

**Solution**: Either:
1. Wait for full recovery between impactful scenarios (~50 min for ransomware)
2. Test the most impactful scenario last
3. Use explicit time ranges in verification queries (e.g., `| filter timestamp > now() - 2m`) to see only recent data

**Lesson**: When testing multiple scenarios sequentially, order matters. Test mild scenarios first, impactful scenarios last.

### Discovery: Naming vs. Behavior Mismatch

**Observation**: "MyChart Credential Stuffing Attack" maps to `mychart_peak` and produces normal peak activity, not attack patterns. This kind of naming mismatch is only discoverable through end-to-end testing — code review alone would miss it because the mapping looks intentional.

**Lesson**: Always validate scenario behavior by observing actual generated events, not by reading the scenario name or description. The scenario metadata can promise things the generator doesn't deliver.

### Insight: DQL Default Timeframes Create Hidden Dependencies

**Discovery**: `fetch logs` without an explicit time range uses a sliding 30-minute window. This creates a hidden dependency between sequential scenario tests — each test's "baseline" includes data from the previous test.

**Impact on prompting**: When the agent reports "health indicators are RED," you need additional context to determine if it's the active scenario causing it or residual data from a previous scenario. The agent must track which scenarios have been run and when.

### Effective Pattern: Standing Recovery Verification

**Pattern**: After deactivating a scenario, schedule periodic re-checks at increasing intervals (3min, 8min, 18min, 28min, 48min) until all indicators return to GREEN.

**Why it works**: The recovery curve is gradual, not instant. Checking once and declaring "not recovered" would be premature. The agent needs patience and a systematic approach to track the gradual recovery.

**Quantitative result**: Recovery follows an approximately linear curve for percentage metrics: the ratio of anomalous events decreases as baseline events dilute them in the sliding window.
