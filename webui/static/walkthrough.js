/* Scenario Walkthrough — Frontend Logic */

const DT_APP_URL = "https://gyz6507h.sprint.apps.dynatracelabs.com/ui/apps/my.healthcare.health.monitoring";

const SCENARIO_DATA = {
  "normal-day-shift": {
    icon: "🏥",
    prep: {
      activateMinsBefore: 5,
      totalRuntime: "Continuous (no fixed end)",
      summary: "Baseline scenario — runs continuously. Activate at least 5 minutes before the demo so the DT app has enough data points to render smooth time-series charts.",
      steps: [
        { when: "T-5 min", action: "Activate 'Normal Day Shift' from the Control Panel", why: "The generator needs ~3 ticks (30s) to start emitting logs, plus ~1-2 min for Dynatrace ingestion and indexing." },
        { when: "T-3 min", action: "Open the DT Healthcare app and navigate to Overview", why: "Verify data is flowing — you should see the System Activity timeline begin populating." },
        { when: "T-0", action: "Begin your demo", why: "You now have 5 min of baseline data showing normal curves — enough for the Overview, Epic Health, and Network charts to look realistic." }
      ],
      proTip: "For the best-looking demo, activate 15+ minutes before. Longer baseline = smoother time-series curves and more realistic time-of-day patterns."
    },
    dtPages: [
      { page: "Overview (/)", items: ["All KPIs green — login rate >98%, HL7 delivery 100%", "System Activity timeline shows steady volumes", "Campus map — all 4 sites reporting"] },
      { page: "Epic Health (/epic)", items: ["Login volume follows time-of-day curve (peak 10AM-2PM)", "Clinical orders show mix of STAT, Routine, PRN", "No security events beyond routine break-the-glass"] },
      { page: "Network Health (/network)", items: ["All 22 devices reporting, CPU/mem in normal range", "Traffic patterns follow clinical schedule", "NetFlow — mostly internal, clinical protocols"] },
      { page: "Integration (/integration)", items: ["HL7 messages at steady 7AM-7PM rate", "FHIR API p95 <200ms, no errors", "ETL jobs completing on schedule"] }
    ],
    steps: [
      { title: "Show the Overview", text: "Point out all 6 KPIs are green. The campus map shows all sites healthy. This is the baseline everything else deviates from." },
      { title: "Walk through Epic Health", text: "Show login volume follows a natural bell curve. Orders are a mix of types. Security events table is quiet — maybe 1-2 routine break-the-glass." },
      { title: "Check Network Health", text: "Device fleet honeycomb is cool-colored (low CPU). All 22 devices last-seen within 5 min. Traffic is predictable." },
      { title: "Verify Integrations", text: "HL7, FHIR, ETL all green. This is the target state. Every scenario creates deviations FROM this baseline." }
    ],
    talking: [
      { icon: "📊", text: "This is what 'normal' looks like — the baseline for anomaly detection." },
      { icon: "🔑", text: "Key: the DT app can spot deviations from this pattern across ALL subsystems simultaneously." },
      { icon: "💡", text: "In a real hospital, these patterns change by shift (day vs night) and day of week. Our generator models these curves." }
    ]
  },
  "normal_shift": {
    icon: "🏥",
    aliasOf: "normal-day-shift"
  },
  "ed-surge": {
    icon: "🚨",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "Continuous (no fixed end)",
      summary: "ED Surge generates 1.5x normal event volume with concentrated ED department activity. Activate 10 minutes before the demo to build up enough volume contrast against the baseline.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish baseline", why: "The ED surge is most impactful when there's a visible spike compared to normal baseline. Without baseline data, the spike won't be obvious." },
        { when: "T-10 min", action: "Switch to 'ED Surge' from the Control Panel", why: "The generator restarts with 1.5x volume multiplier and ED-focused event weights. You need 8-10 min for the volume spike to be clearly visible in DT charts." },
        { when: "T-3 min", action: "Open the DT Healthcare app → Overview", why: "Verify the System Activity timeline shows a clear inflection point where volume spikes up." },
        { when: "T-0", action: "Begin demo at Overview — 'Something just happened...'", why: "The audience can see the exact moment the surge began. Start the story from the spike." }
      ],
      proTip: "If time permits, run baseline for 15 min then switch. The longer the baseline, the more dramatic the spike looks on the Overview timeline."
    },
    dtPages: [
      { page: "Overview (/)", items: ["Total Epic Events spike sharply", "Login success rate may dip under load", "System Activity shows correlated spike across Epic and Network"] },
      { page: "Epic Health (/epic)", items: ["Login volume surges — many simultaneous clinicians logging in", "Clinical orders: STAT orders 8x baseline", "Department Activity: ED dominates the top"] },
      { page: "Integration (/integration)", items: ["HL7 ADT A01 (admit) messages spike 5x", "FHIR API response times increase (p95 may breach 500ms)", "ETL may show delayed completion"] },
      { page: "Network Health (/network)", items: ["ED VLAN devices show higher CPU/traffic", "Network traffic spike correlates with clinical activity", "NetFlow: ED subnet traffic dominates"] }
    ],
    steps: [
      { title: "Start at Overview — notice the spike", text: "Total events jump. The System Activity timeline shows a sharp inflection point. Ask: 'What just happened?'" },
      { title: "Drill into Epic Health", text: "Show the login volume spike. Department Activity bar chart should have ED at top. Order Volume shows STAT orders dominating." },
      { title: "Check Integration Health", text: "HL7 volume spikes — these are ADT admits. FHIR response times increase. Point out this is normal behavior under surge." },
      { title: "Correlate with Network", text: "Show Network Health — ED access switch CPU/traffic correlates. This proves the surge is real (not a system error)." }
    ],
    talking: [
      { icon: "🚑", text: "Mass casualty incidents create a predictable surge pattern — the DT app lets you see it across ALL systems." },
      { icon: "🔗", text: "Cross-correlation is key: HL7 ADT spike + login spike + network spike = real clinical surge vs. system glitch." },
      { icon: "⚠️", text: "In a real MCI, IT needs to ensure systems can handle load. These dashboards show when you're approaching capacity." }
    ]
  },
  "ed_surge": {
    icon: "🚨",
    aliasOf: "ed-surge"
  },
  "ransomware-attack": {
    icon: "💀",
    prep: {
      activateMinsBefore: 30,
      totalRuntime: "60 min (4 phases: Recon 20m → Credential Harvest 10m → Lateral Movement 20m → Exfiltration 10m)",
      summary: "This is the flagship demo scenario. It runs a 4-phase attack kill chain over 60 minutes. For a full kill-chain demo, activate 30+ minutes before. For a quick 'attack in progress' demo, 10 minutes is sufficient (you'll catch the middle phases).",
      steps: [
        { when: "T-35 min (full demo)", action: "Activate 'Normal Day Shift' to establish clean baseline", why: "A clean baseline makes the attack anomalies stand out dramatically. The audience needs to see 'this is normal' before 'this is not.'" },
        { when: "T-30 min", action: "Switch to 'Ransomware Attack' from the Control Panel", why: "Phase 1 (Reconnaissance) starts immediately — failed logins from 172.16.99.x, service account probing. This phase runs for 20 min." },
        { when: "T-20 min", action: "Optionally check Overview — early indicators should be appearing", why: "Login success rate should be dropping. Security Events table shows FAILEDLOGIN and WPSEC_LOGIN_FAIL from unusual IPs." },
        { when: "T-10 min", action: "Phase 2 (Credential Harvesting) is now active", why: "Successful logins appear from the attacker IP range. 2FA events. The attacker has valid credentials now." },
        { when: "T-0", action: "Begin demo — you're in Phase 3 (Lateral Movement) or Phase 4 (Exfiltration)", why: "The most dramatic phases: break-the-glass events, sequential patient chart access, mass record exfiltration. All 4 phases visible in the timeline." }
      ],
      proTip: "For the most impactful demo, start presenting at T-10 min (during Credential Harvesting) so the audience watches Phase 3 and 4 unfold live. Say: 'Let me show you an attack that started 20 minutes ago — and watch what happens next.'"
    },
    dtPages: [
      { page: "Epic Health (/epic)", items: ["Security Events table: break-the-glass from service accounts", "Failed login burst from satellite IP range 172.16.99.x", "Sequential patient chart lookups (automated exfil pattern)"] },
      { page: "Network Health (/network)", items: ["Wellington firewall (wel-fw-01) shows threat alerts", "WAN traffic between Wellington→KCRMC spikes 10x", "NetFlow: high-volume HTTPS to single external IP (C2)"] },
      { page: "Overview (/)", items: ["Login Success Rate KPI drops to CRITICAL (< 70%)", "Epic↔Network Correlation chart shows coordinated anomaly", "Events by Site: Wellington satellite activity spike"] },
      { page: "Security & Compliance (/security)", items: ["After-hours access from non-clinical admin accounts", "Break-the-glass events cluster from service accounts", "Source IP analysis shows satellite origin"] }
    ],
    steps: [
      { title: "Start with the Overview — see the red", text: "Login Success Rate is RED. Multiple KPIs degraded. Ask: 'Something is clearly wrong — but what exactly?'" },
      { title: "Pivot to Epic Health — the attack surface", text: "Security Events table shows break-the-glass from service accounts. Failed logins from 172.16.99.x. Sequential patient MRN lookups = automated exfiltration." },
      { title: "Show Network Health — the entry point", text: "Wellington firewall shows threat alerts. WAN traffic spikes. NetFlow reveals data flowing to external IP. This is the initial compromise at the satellite clinic." },
      { title: "Tell the kill chain story", text: "Phishing at Wellington → credential theft → WAN pivot to KCRMC → Epic compromise → patient data exfiltration. The DT app shows the ENTIRE chain across all domains." }
    ],
    talking: [
      { icon: "🎯", text: "Healthcare ransomware targets patient data. The kill chain: phish → credential → pivot → exfiltrate." },
      { icon: "🔗", text: "Cross-domain correlation is the ONLY way to see this. Network alone misses the Epic impact. Epic alone misses the entry point." },
      { icon: "⏱️", text: "Time-to-detect is critical. This dashboard shows the attack timeline — enabling faster incident response." },
      { icon: "📋", text: "HIPAA requires breach notification within 60 days. Early detection through observability reduces breach scope." }
    ]
  },
  "ransomware": {
    icon: "💀",
    aliasOf: "ransomware-attack"
  },
  "brute_force": {
    icon: "🔐",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "60 min (360 ticks × 10s), but RED indicators appear within 5 min",
      summary: "Brute force generates 8 failed login events per tick from the 192.168.99.x range. Login Success Rate drops from ~97% to ~57% within 3-5 minutes — turning the KPI RED in the DT app. Quick to show impact.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish healthy baseline", why: "The login success rate needs to be GREEN (>85%) first so the drop to RED is dramatic." },
        { when: "T-10 min", action: "Switch to 'Brute Force Attack' from the Control Panel", why: "Failed logins start immediately — 8 per tick. Within 3 min, enough FAILEDLOGIN and LOGIN_BLOCKED events exist to move the success rate KPI." },
        { when: "T-5 min", action: "Open DT app → Overview and verify Login Success Rate is dropping", why: "The KPI should be YELLOW (~70-85%) within 3 min and RED (<70%) within 5 min. If you see this, the demo is ready." },
        { when: "T-0", action: "Begin demo — Login Success Rate should be solidly RED", why: "The audience immediately sees a red KPI. 'Let's investigate why logins are failing.'" }
      ],
      proTip: "This is the fastest scenario to show impact. Good for time-constrained demos. 10 min of prep is plenty. Login success drops to ~57% — well into RED territory."
    },
    dtPages: [
      { page: "Overview (/)", items: ["Login Success Rate KPI turns RED (< 70%)", "Total Epic Events elevated due to failed login flood", "System Activity timeline shows spike in security events"] },
      { page: "Epic Health (/epic)", items: ["Login volume chart shows massive failure spike", "Security Events table: FAILEDLOGIN, LOGIN_BLOCKED, WPSEC_LOGIN_FAIL", "Source IPs concentrated in 192.168.99.0/24 range"] },
      { page: "Security & Compliance (/security)", items: ["Auth Health donut chart shifts heavily toward failures", "Failed login source analysis shows single IP range", "Targeted users: VPHAM, DCANNON, LCUNEAZ, RSTOJAN"] }
    ],
    steps: [
      { title: "Overview — spot the red KPI", text: "Login Success Rate is RED at ~57%. This is the entry point. Ask: 'Why are logins failing?'" },
      { title: "Drill into Epic Health", text: "Security Events table is flooded with FAILEDLOGIN and LOGIN_BLOCKED from 192.168.99.x. The attacker is testing credentials systematically." },
      { title: "Show the pattern", text: "Same IP range, same 4 target usernames, repeated attempts. This is automated brute-force, not a user who forgot their password." },
      { title: "Discuss response", text: "In a real scenario: block the IP range at the firewall, force password resets for targeted accounts, enable MFA if not already active." }
    ],
    talking: [
      { icon: "🔐", text: "Brute force is the simplest attack pattern — but it's still effective when MFA isn't enforced." },
      { icon: "📊", text: "Detection signal: login failure rate spike + concentrated source IP = brute force. The KPI catches it immediately." },
      { icon: "⚡", text: "This is the fastest demo to show value. KPI turns red in under 5 minutes. Great for time-constrained demos." }
    ]
  },
  "hipaa_audit": {
    icon: "📋",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "60 min (360 ticks × 10s)",
      summary: "Simulates a billing department employee (OTESTADMIN) performing excessive patient lookups across 6 unrelated departments. Generates 10 audit events per tick — PUL_SEARCH_AUDIT, WPSEC_PATIENT_LOOKUP_ATTEMPT, and CHART_ACCESS. Detectable within 5-8 minutes.",
      steps: [
        { when: "T-10 min", action: "Activate 'HIPAA Audit' from the Control Panel", why: "The anomaly events start immediately. You need 5-8 min for enough PUL_SEARCH_AUDIT events to appear as a clear pattern in DT." },
        { when: "T-5 min", action: "Open DT app → Security & Compliance", why: "Check that patient lookup events are appearing. You should see OTESTADMIN (Billing) accessing Psychiatry, L&D, Oncology, etc." },
        { when: "T-0", action: "Begin demo — focus on the cross-department access pattern", why: "The audience sees a single billing user accessing clinical records across 6+ departments — a clear HIPAA red flag." }
      ],
      proTip: "Pair with the Insider Threat or Privacy Breach scenario for a comprehensive 'workforce compliance' demo track. Run HIPAA first (10 min), then switch to Insider Threat."
    },
    dtPages: [
      { page: "Security & Compliance (/security)", items: ["Patient lookup volume by user — OTESTADMIN far above others", "Cross-department access pattern: Billing user in Psychiatry, L&D, Oncology, Emergency, Pediatrics, ICU", "Audit trail shows systematic browsing, not clinical need"] },
      { page: "Epic Health (/epic)", items: ["Security Events table: PUL_SEARCH_AUDIT flooding from single user", "WPSEC_PATIENT_LOOKUP_ATTEMPT events elevated", "CHART_ACCESS events across multiple departments"] },
      { page: "Overview (/)", items: ["Total Epic Events slightly elevated", "Security event count higher than baseline"] }
    ],
    steps: [
      { title: "Start at Security & Compliance", text: "Patient lookup activity shows one user — OTESTADMIN from Billing — accessing records across 6 clinical departments. That's not normal." },
      { title: "Show the department spread", text: "Psychiatry, L&D, Oncology, Emergency, Pediatrics, ICU-East. A billing user has no clinical reason to be in any of these." },
      { title: "Examine the access pattern", text: "Sequential searches, rapid chart access, no associated orders or clinical actions. This is browsing, not treating." },
      { title: "Discuss HIPAA implications", text: "Each unauthorized access is a potential HIPAA violation. The pattern suggests either curiosity-driven snooping or data harvesting." }
    ],
    talking: [
      { icon: "📋", text: "HIPAA's Minimum Necessary Standard: access should be limited to what's required for the job. Billing doesn't need psychiatric records." },
      { icon: "🔍", text: "The key detection pattern: single user + many departments + no clinical justification = audit trigger." },
      { icon: "⚖️", text: "Penalties: $100-$50K per violation, up to $1.5M per category per year. Each chart access could be a separate violation." }
    ]
  },
  "insider-threat-snooping": {
    icon: "🕵️",
    prep: {
      activateMinsBefore: 15,
      totalRuntime: "50 min (300 ticks × 10s)",
      summary: "Simulates a night-shift Med-Surg nurse (SBRYANT) accessing VIP and coworker records via break-the-glass. Low volume (4 events/tick) and 0.2x normal volume — this is a 'low and slow' attack that's intentionally hard to detect. Give it 10-15 min for enough break-the-glass events to form a visible cluster.",
      steps: [
        { when: "T-15 min", action: "Activate 'Insider Threat' from the Control Panel", why: "This scenario runs at 0.2x normal volume (simulating quiet night shift). Events are sparse — you need 10-15 min to accumulate enough break-the-glass events for a clear pattern." },
        { when: "T-5 min", action: "Open DT app → Epic Health → Security Events", why: "Verify AC_BREAK_THE_GLASS_ACCESS events are appearing from SBRYANT. You should see 3-5 break-the-glass events by now." },
        { when: "T-0", action: "Begin demo — 'This looks quiet, but something is wrong'", why: "The demo narrative is about finding the needle in the haystack. The low volume IS the point." }
      ],
      proTip: "Deliver this as a mystery story: 'Everything looks normal — low volume, night shift. But watch the Security Events table closely...'"
    },
    dtPages: [
      { page: "Epic Health (/epic)", items: ["Security Events: AC_BREAK_THE_GLASS_ACCESS from SBRYANT (Med-Surg 4W)", "Department access: records from Executive Health, VIP patients, coworkers", "After-hours timing: 11PM-3AM window, single workstation"] },
      { page: "Security & Compliance (/security)", items: ["Break-the-glass count by user — SBRYANT far above normal for night shift", "After-hours access pattern visualization", "VIP patient access audit trail", "Access justifications: 'Continuity of Care', 'Direct Care', or blank"] },
      { page: "Overview (/)", items: ["Overall volume is LOW — this is easy to miss", "Active users count minimal (night shift)", "No network anomalies — purely behavioral detection"] }
    ],
    steps: [
      { title: "Start with the Overview — it looks fine", text: "Volume is low. KPIs are green. Night shift. The audience thinks everything is okay. This is the setup." },
      { title: "Now look at Epic Health Security Events", text: "One user — SBRYANT, Med-Surg 4W nurse — has multiple break-the-glass events. She's accessing Executive Health patients. That's not her department." },
      { title: "Examine the access sequence", text: "Login → Search (VIP name) → Break-the-glass → Chart Access → Search (coworker name) → Break-the-glass → Chart Access. Sequential snooping." },
      { title: "Why this is hard to detect", text: "No network anomalies. No system errors. Low volume. Valid credentials. Only the PATTERN of access — cross-department break-the-glass at 2AM — reveals the threat." }
    ],
    talking: [
      { icon: "🕵️", text: "Insider threats are the hardest to detect because they use legitimate credentials and normal access tools." },
      { icon: "📋", text: "HIPAA: unauthorized access to PHI is a breach even if no data leaves the building. Each break-the-glass event is auditable." },
      { icon: "🔑", text: "Detection requires behavioral analytics: WHO accessed WHAT, WHEN, and was it appropriate for their role?" },
      { icon: "💡", text: "The justification field matters: 'Continuity of Care' for a patient in a different department at 2AM? That doesn't pass the smell test." }
    ]
  },
  "insider_threat": {
    icon: "🕵️",
    aliasOf: "insider-threat-snooping"
  },
  "privacy_breach": {
    icon: "🔓",
    prep: {
      activateMinsBefore: 15,
      totalRuntime: "50 min (300 ticks × 10s)",
      summary: "Similar to Insider Threat but more aggressive — user NTESTADMIN performs break-the-glass abuse across Psychiatry, L&D, and Oncology with 'Administrative Review' as the justification. Runs at 0.3x volume (simulating after-hours). 5 events per tick.",
      steps: [
        { when: "T-15 min", action: "Activate 'Privacy Breach' from the Control Panel", why: "After-hours scenario at 0.3x volume. Needs time for break-the-glass patterns to accumulate." },
        { when: "T-5 min", action: "Open DT app → Security & Compliance", why: "Verify AC_BREAK_THE_GLASS_ACCESS events appearing from NTESTADMIN with 'Administrative Review' justification." },
        { when: "T-0", action: "Begin demo — focus on the break-the-glass pattern", why: "The story: someone is using 'Administrative Review' to bypass access controls on sensitive departments." }
      ],
      proTip: "Good follow-up to the HIPAA Audit scenario. HIPAA shows excessive lookups; Privacy Breach shows the next escalation — actually accessing restricted records via break-the-glass abuse."
    },
    dtPages: [
      { page: "Security & Compliance (/security)", items: ["Break-the-glass events from NTESTADMIN with 'Administrative Review' override", "Target departments: Psychiatry, L&D, Oncology — all sensitive", "After-hours timing: 10PM-2AM window"] },
      { page: "Epic Health (/epic)", items: ["Security Events table: AC_BREAK_THE_GLASS_ACCESS, CHART_ACCESS, PUL_SEARCH_AUDIT", "Single user generating disproportionate security events", "Sensitive department access pattern"] }
    ],
    steps: [
      { title: "Security & Compliance — break-the-glass abuse", text: "NTESTADMIN is overriding access controls using 'Administrative Review' to access Psychiatry, L&D, and Oncology records." },
      { title: "Examine the justification", text: "'Administrative Review' on psychiatric records at midnight? This isn't an audit — it's a breach." },
      { title: "Show the target departments", text: "Psychiatry, L&D (Labor & Delivery), Oncology — these are the most sensitive departments in a hospital. This is targeted." },
      { title: "Discuss the response", text: "Immediate: revoke access, preserve audit trail. Investigation: review all records accessed. Notification: HIPAA breach assessment required." }
    ],
    talking: [
      { icon: "🔓", text: "Break-the-glass is an emergency override — it's not meant for 'Administrative Review' of psychiatric records at midnight." },
      { icon: "⚖️", text: "Psychiatric, substance abuse, and reproductive health records have EXTRA protections under state and federal law." },
      { icon: "📋", text: "Every break-the-glass access is logged. The justification becomes evidence if this reaches HHS OCR." }
    ]
  },
  "epic-outage-network-root-cause": {
    icon: "🔌",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "Continuous — network events trigger cascading Epic failures",
      summary: "Core switch interface flap → Citrix ADC → F5 → Epic outage. The temporal ordering is the key insight: network fails FIRST, then Epic. Activate 10 min before to see the full cascade in the DT timeline.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish healthy baseline", why: "All KPIs need to be green first. The cascade is most impactful when everything was fine and then suddenly breaks." },
        { when: "T-10 min", action: "Switch to 'Epic Outage — Network Root Cause'", why: "Network events start immediately (interface flap). Citrix and F5 impact follows within 1-2 min. Epic login failures cascade 3-5 min after." },
        { when: "T-3 min", action: "Check DT app → Overview — KPIs should be going red", why: "Login rate drops, device health degrades. Verify the cascade is visible." },
        { when: "T-0", action: "Begin demo at Overview — 'Multiple systems are failing...'", why: "The audience sees simultaneous failures. The demo is about finding the ROOT CAUSE — which is network, not Epic." }
      ],
      proTip: "This is the best demo for showing Dynatrace's cross-domain correlation value. The punchline: 'Everyone thought Epic was down. It was actually a bad switch port.'"
    },
    dtPages: [
      { page: "Network Health (/network)", items: ["Core switch interface flap (UPDOWN) — this is the FIRST event", "Citrix VServer down 10 seconds later", "F5 pool member down — confirms wider impact"] },
      { page: "Epic Health (/epic)", items: ["Login failures spike AFTER network events — proves root cause", "FHIR API 503 errors appear", "Active users drops sharply"] },
      { page: "Integration (/integration)", items: ["FHIR status shows 5xx spike", "HL7 delivery rate may dip", "FHIR response times go to timeout"] },
      { page: "Overview (/)", items: ["Epic↔Network Correlation: network drop PRECEDES Epic drop", "Multiple KPIs degraded simultaneously"] }
    ],
    steps: [
      { title: "Start at Overview — see the cliff", text: "Multiple KPIs drop simultaneously. Login rate tanks. This looks like an Epic outage. But is it?" },
      { title: "Check Network Health FIRST", text: "Core switch interface flap is the FIRST event. Citrix goes down 10s later. F5 follows. This is the root cause chain." },
      { title: "Now look at Epic Health", text: "Login failures start AFTER the network events. This proves Epic isn't the problem — the network is." },
      { title: "Show the recovery order", text: "Network up → Citrix up → F5 up → Epic logins resume. The cascade proves causation direction." }
    ],
    talking: [
      { icon: "🔑", text: "ROOT CAUSE ANALYSIS: The key insight is temporal ordering. Network fails FIRST, then Epic. Not the other way around." },
      { icon: "🏥", text: "In healthcare, misdiagnosing an Epic outage wastes critical time. Cross-domain visibility finds the real cause." },
      { icon: "⚡", text: "MTTR reduction: knowing it's a network issue lets you dispatch the right team immediately." }
    ]
  },
  "hl7-interface-failure": {
    icon: "🔀",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "Continuous — network port error causes HL7 stall then recovery",
      summary: "Access switch port CRC errors on VLAN 30 disable the HL7 interface. Lab results stop flowing. Clinicians start entering duplicate orders. When the port recovers, queued messages flush through as a burst.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish baseline HL7 flow", why: "You want the Integration page to show a healthy HL7 delivery rate before it drops to 0%." },
        { when: "T-10 min", action: "Switch to 'HL7 Interface Failure'", why: "Port errors start → HL7 traffic drops to zero. Within 5 min the Integration page shows the HL7 cliff." },
        { when: "T-3 min", action: "Verify Integration page shows HL7 delivery at 0%", why: "The scenario is ready when you can see the cliff and the gap." },
        { when: "T-0", action: "Begin demo — 'Lab results aren't showing up in Epic...'", why: "Start with the clinical complaint, then trace to root cause." }
      ],
      proTip: "Present as a help-desk ticket scenario: 'Nurse calls: I ordered labs 2 hours ago and there are no results in Epic.' Then investigate."
    },
    dtPages: [
      { page: "Integration (/integration)", items: ["HL7 delivery rate drops to 0%", "HL7 volume timeline shows cliff, then flush burst on recovery", "Failed ETL jobs table populates (downstream impact)"] },
      { page: "Network Health (/network)", items: ["Access switch port CRC errors on VLAN 30", "Zero traffic on HL7 VLAN during err-disable", "Traffic burst when port comes back up"] },
      { page: "Epic Health (/epic)", items: ["Duplicate clinical orders (staff re-entering)", "Lab/pharmacy department activity patterns disrupted"] },
      { page: "Overview (/)", items: ["HL7 Delivery KPI drops — most visible indicator", "Epic↔Network correlation shows gap then burst"] }
    ],
    steps: [
      { title: "See the Integration impact first", text: "HL7 delivery rate drops to 0%. Volume timeline shows a cliff. 'Lab results aren't showing up in Epic.'" },
      { title: "Find the root cause in Network", text: "Switch port on VLAN 30 has CRC errors → err-disable. Zero HL7 traffic confirms. Bad cable or SFP." },
      { title: "Show the clinical impact", text: "Epic Health shows duplicate orders — staff re-entering because results never arrived. This is the patient safety risk." },
      { title: "Show the recovery burst", text: "When the port comes back, queued HL7 messages flood through. Visible as a spike in both HL7 volume and NetFlow." }
    ],
    talking: [
      { icon: "🔬", text: "HL7 interfaces are the nervous system of a hospital. A single bad cable can stop lab results from reaching clinicians." },
      { icon: "⚠️", text: "Clinical impact: duplicate orders, delayed results, potential medication errors. This is a patient safety scenario." },
      { icon: "🔗", text: "Network observability + HL7 monitoring together pinpoint the exact cause instantly." }
    ]
  },
  "iomt-device-compromise": {
    icon: "💉",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "Continuous — compromised device scanning detected then contained",
      summary: "A compromised infusion pump on VLAN 40 starts lateral scanning. IPS alerts fire. The scenario shows micro-segmentation containing the threat before it reaches the HL7 interface.",
      steps: [
        { when: "T-10 min", action: "Activate 'IoMT Device Compromise'", why: "Network events (IPS alerts, port security violations) start immediately. Need 5-8 min for enough events to show the scan pattern." },
        { when: "T-3 min", action: "Verify Network Health shows VLAN 40 alerts", why: "IPS alerts and anomalous traffic patterns should be visible. Port security violation is the earliest indicator." },
        { when: "T-0", action: "Begin demo — 'An IoMT device is behaving strangely...'", why: "Start from the network perspective — a medical device doing port scans." }
      ],
      proTip: "Good for healthcare-specific audience. Emphasize that medical devices can't be patched easily — network segmentation is the primary defense."
    },
    dtPages: [
      { page: "Network Health (/network)", items: ["IPS alerts on VLAN 40 (medical device VLAN)", "Port security violation — earliest detection point", "Anomalous traffic: IoMT device scanning multiple ports"] },
      { page: "Overview (/)", items: ["NetFlow: unusual traffic from 10.10.40.x subnet", "Firewall deny rules contain the compromise"] },
      { page: "Integration (/integration)", items: ["Potential HL7 port (2575) connection attempt from IoMT device", "This is the critical 'blast radius' indicator"] }
    ],
    steps: [
      { title: "Start with Network — the compromise source", text: "Port security violation on VLAN 40. An infusion pump is doing things it should never do." },
      { title: "Show the lateral scan", text: "NetFlow shows the device scanning multiple ports and IPs. It's trying to reach the HL7 interface on port 2575." },
      { title: "Show the containment", text: "Firewall deny rules block the lateral movement. Micro-segmentation contains the blast radius." },
      { title: "Discuss the patient safety angle", text: "A compromised infusion pump is a patient safety risk. Network segmentation is the critical control." }
    ],
    talking: [
      { icon: "💉", text: "IoMT devices run legacy OS, rarely patched. They're the softest targets in a hospital network." },
      { icon: "🛡️", text: "Micro-segmentation (VLANs + firewall rules) is the primary defense. This scenario shows it working." },
      { icon: "⚠️", text: "If the device reaches HL7 (port 2575), it could inject malicious messages. This is a patient safety scenario." }
    ]
  },
  "mychart-credential-stuffing": {
    icon: "🤖",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "Continuous — sustained credential stuffing attack",
      summary: "Automated credential stuffing against the MyChart patient portal. Login failure rate spikes 500x. Login Success Rate KPI drops sharply. ~1.5% of attempts succeed → PHI access.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish baseline login rate", why: "Login success rate needs to be at 97-98% baseline for the drop to be visible." },
        { when: "T-10 min", action: "Switch to 'MyChart Credential Stuffing'", why: "Failed MyChart logins start flooding. Within 3-5 min the login success rate KPI starts dropping." },
        { when: "T-5 min", action: "Verify Overview shows login success rate declining", why: "Should be dropping toward YELLOW. By T-0 it should be RED." },
        { when: "T-0", action: "Begin demo — 'Our patient portal is under attack'", why: "Login KPI is red. The audience sees the scale of the attack immediately." }
      ],
      proTip: "Pair with Brute Force for a 'credential attacks' demo track. Brute force targets Epic staff logins; credential stuffing targets patient portal. Different vectors, same observability platform."
    },
    dtPages: [
      { page: "Overview (/)", items: ["Login Success Rate KPI drops sharply", "Active users count anomalous (includes bot sessions)", "System Activity shows massive event spike"] },
      { page: "Epic Health (/epic)", items: ["Login failure rate spikes — FAILEDLOGIN, LOGIN_BLOCKED, WPSEC_LOGIN_FAIL flood", "Login volume chart shows massive failure spike", "Some successful logins from the attack — these are the breached accounts"] },
      { page: "Network Health (/network)", items: ["NetFlow: distributed source IPs (botnet)", "External source countries show unusual geography", "Citrix ADC connection count mirrors failure rate"] },
      { page: "Security & Compliance (/security)", items: ["Auth Health donut shifts toward failures", "Failed login source analysis shows distributed IPs", "Successful stuffed logins → PHI access events"] }
    ],
    steps: [
      { title: "Overview — Login Success Rate drops", text: "The first thing you notice: login success rate drops from 98% to maybe 60%. Something is hammering the portal." },
      { title: "Epic Health — see the flood", text: "Login volume chart shows massive failure spike. Security Events table is full of FAILEDLOGIN and LOGIN_BLOCKED." },
      { title: "Network — trace the botnet", text: "NetFlow shows distributed source IPs — hundreds of IPs hitting MyChart. External countries chart confirms geographic spread." },
      { title: "The breach — successful logins", text: "~1.5% of credential stuffing succeeds. Those sessions access PHI. This is the data breach moment." }
    ],
    talking: [
      { icon: "🤖", text: "Credential stuffing uses leaked username/password pairs from other breaches. Automated bots test millions." },
      { icon: "📊", text: "Detection signal: massive login failures from diverse IPs + small percentage of successes = classic stuffing pattern." },
      { icon: "🛡️", text: "Mitigations: rate limiting, MFA, CAPTCHA, WAF rules. The observability platform detects the pattern in real-time." },
      { icon: "⚠️", text: "Even a 1.5% success rate = hundreds of compromised patient accounts. Each is a HIPAA breach." }
    ]
  },
  "mychart_peak": {
    icon: "📱",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "Continuous (no fixed end)",
      summary: "Patient portal peak — 3x MyChart multiplier simulating evening hours when patients check test results, send messages, and request refills. Not an attack scenario — shows healthy portal usage patterns.",
      steps: [
        { when: "T-10 min", action: "Activate 'MyChart Peak Usage'", why: "Needs time to build up MyChart-weighted event patterns." },
        { when: "T-3 min", action: "Check Epic Health for MyChart event patterns", why: "MyChart events should dominate the event type distribution." },
        { when: "T-0", action: "Begin demo", why: "Show healthy patient portal engagement patterns." }
      ],
      proTip: "Good baseline for contrasting with MyChart Credential Stuffing. Show 'this is normal MyChart traffic' then switch to the attack."
    },
    dtPages: [
      { page: "Epic Health (/epic)", items: ["MyChart events dominate event type distribution", "Patient portal actions: result views, messaging, refill requests", "Login patterns show evening peak"] },
      { page: "Overview (/)", items: ["Event distribution weighted toward MyChart", "Overall volume moderate (0.8x multiplier)"] }
    ],
    steps: [
      { title: "Show MyChart event distribution", text: "Portal traffic is high — result views, messages, refills. This is healthy patient engagement." },
      { title: "Contrast with clinical volume", text: "Clinical events are lower (evening, fewer staff). MyChart is 40% of events vs. 10% during normal shift." },
      { title: "Note the time-of-day pattern", text: "Peak between 5PM-9PM — patients checking results after work. Natural and expected." }
    ],
    talking: [
      { icon: "📱", text: "MyChart engagement is a positive metric for health systems. High portal usage = better patient outcomes." },
      { icon: "📊", text: "Monitoring portal usage helps capacity planning: when do patients hit the portal, and can the infrastructure handle it?" }
    ]
  }
};

/* Resolve aliases */
function getScenarioData(key) {
  let data = SCENARIO_DATA[key];
  if (data && data.aliasOf) data = SCENARIO_DATA[data.aliasOf];
  return data || null;
}

async function loadScenarios() {
  const res = await fetch("/api/scenarios");
  const scenarios = await res.json();
  const grid = document.getElementById("scenario-selector");
  grid.innerHTML = scenarios.map(s => {
    const data = getScenarioData(s.key) || {};
    return `<button class="scenario-btn" data-key="${s.key}" onclick="showWalkthrough('${s.key}')">
      <div class="scenario-btn-name">${data.icon || "📋"} ${escHtml(s.name)}</div>
      <div class="scenario-btn-badges">
        <span class="badge badge-epic">Epic</span>
        ${s.has_network_correlation ? '<span class="badge badge-network">Network</span>' : ''}
      </div>
    </button>`;
  }).join("");
}

function showWalkthrough(key) {
  const data = getScenarioData(key);
  if (!data) return;

  // Update selector buttons
  document.querySelectorAll(".scenario-btn").forEach(b => b.classList.remove("active"));
  const activeBtn = document.querySelector(`[data-key="${key}"]`);
  if (activeBtn) activeBtn.classList.add("active");

  // Populate header
  document.getElementById("wt-icon").textContent = data.icon;
  const nameEl = activeBtn?.querySelector(".scenario-btn-name");
  document.getElementById("wt-name").textContent = nameEl ? nameEl.textContent.slice(2).trim() : key;

  // Fetch scenario description + indicators
  fetch(`/api/scenarios`).then(r => r.json()).then(scenarios => {
    const s = scenarios.find(x => x.key === key);
    if (s) {
      document.getElementById("wt-desc").textContent = s.description;
      document.getElementById("wt-indicators").innerHTML = (s.indicators || []).map((ind, i) =>
        `<div class="indicator-item"><span class="indicator-num">${i+1}</span><span>${escHtml(ind)}</span></div>`
      ).join("") || '<p style="color:var(--text-muted)">Baseline scenario — no anomaly indicators.</p>';
    }
  });

  // Prep section
  const prepEl = document.getElementById("wt-prep");
  if (data.prep) {
    const p = data.prep;
    prepEl.innerHTML = `
      <div class="prep-summary">
        <div class="prep-timing">
          <div class="prep-timing-item"><span class="prep-label">Activate Before Demo</span><span class="prep-value">${p.activateMinsBefore} min</span></div>
          <div class="prep-timing-item"><span class="prep-label">Total Runtime</span><span class="prep-value-sm">${escHtml(p.totalRuntime)}</span></div>
        </div>
        <p class="prep-desc">${escHtml(p.summary)}</p>
      </div>
      <div class="prep-steps">
        ${p.steps.map(s => `
          <div class="prep-step">
            <div class="prep-when">${escHtml(s.when)}</div>
            <div class="prep-detail">
              <div class="prep-action">${escHtml(s.action)}</div>
              <div class="prep-why">${escHtml(s.why)}</div>
            </div>
          </div>
        `).join("")}
      </div>
      ${p.proTip ? `<div class="prep-protip"><span class="protip-label">💡 Pro Tip</span> ${escHtml(p.proTip)}</div>` : ""}
    `;
    document.getElementById("wt-prep-section").style.display = "block";
  } else {
    prepEl.innerHTML = "";
    document.getElementById("wt-prep-section").style.display = "none";
  }

  // DT Pages
  document.getElementById("wt-dtpages").innerHTML = (data.dtPages || []).map(p =>
    `<div class="dt-page-card"><h4>${escHtml(p.page)}</h4><ul>${p.items.map(i => `<li>${escHtml(i)}</li>`).join("")}</ul></div>`
  ).join("");

  // Demo steps
  document.getElementById("wt-steps").innerHTML = (data.steps || []).map(s =>
    `<div class="demo-step"><h4>${escHtml(s.title)}</h4><p>${escHtml(s.text)}</p></div>`
  ).join("");

  // Talking points
  document.getElementById("wt-talking").innerHTML = (data.talking || []).map(t =>
    `<div class="talking-point"><span class="tp-icon">${t.icon}</span><span>${escHtml(t.text)}</span></div>`
  ).join("");

  document.getElementById("walkthrough-content").style.display = "block";
  document.getElementById("walkthrough-content").scrollIntoView({ behavior: "smooth", block: "start" });
}

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

document.addEventListener("DOMContentLoaded", loadScenarios);
