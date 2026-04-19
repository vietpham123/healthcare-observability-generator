/* Scenario Walkthrough — Frontend Logic */

const DT_APP_URL = "https://gyz6507h.sprint.apps.dynatracelabs.com/ui/apps/my.healthcare.health.monitoring";

const SCENARIO_DATA = {
  "normal-day-shift": {
    icon: "🏥",
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
  "ed-surge": {
    icon: "🚨",
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
  "ransomware-attack": {
    icon: "💀",
    dtPages: [
      { page: "Epic Health (/epic)", items: ["Security Events table: break-the-glass from KMOORE (admin, not clinician)", "Failed login burst from satellite IP range 10.20.20.x", "SIEM events: sequential patient lookups (MRN+1, MRN+2...)"] },
      { page: "Network Health (/network)", items: ["Wellington firewall (wel-fw-01) shows threat alerts", "WAN traffic between Wellington→KCRMC spikes 10x", "NetFlow: high-volume HTTPS to single external IP (C2)"] },
      { page: "Overview (/)", items: ["Epic↔Network Correlation chart shows coordinated anomaly", "Events by Site: Wellington satellite activity spike"] },
      { page: "Security Page (NEW)", items: ["After-hours access from non-clinical admin account", "Break-the-glass events cluster from single user", "Source IP analysis shows satellite origin"] }
    ],
    steps: [
      { title: "Start with the Network — the entry point", text: "Wellington firewall shows threat alerts. WAN traffic spikes. NetFlow reveals data flowing to external IP. This is the initial compromise." },
      { title: "Pivot to Epic Health — lateral movement", text: "Security Events table shows KMOORE (admin) doing break-the-glass. Failed login burst from 10.20.20.x. Sequential patient MRN lookups = automated exfil." },
      { title: "Show the Timeline — kill chain", text: "On the Overview, the correlation chart shows: network spike → login failures → break-the-glass → data exfil. All within 30 minutes." },
      { title: "Identify the root cause", text: "Phishing at Wellington → credential theft → WAN pivot to KCRMC → Epic compromise → patient data exfiltration. Full kill chain visible." }
    ],
    talking: [
      { icon: "🎯", text: "Healthcare ransomware targets patient data. The kill chain: phish → credential → pivot → exfiltrate." },
      { icon: "🔗", text: "Cross-domain correlation is the ONLY way to see this. Network alone misses the Epic impact. Epic alone misses the entry point." },
      { icon: "⏱️", text: "Time-to-detect is critical. This dashboard shows the attack timeline — enabling faster incident response." },
      { icon: "📋", text: "HIPAA requires breach notification within 60 days. Early detection through observability reduces breach scope." }
    ]
  },
  "epic-outage-network-root-cause": {
    icon: "🔌",
    dtPages: [
      { page: "Network Health (/network)", items: ["Core switch interface flap (UPDOWN) — FIRST event", "Citrix VServer down 10 seconds later", "F5 pool member down confirms wider impact"] },
      { page: "Epic Health (/epic)", items: ["Login failures spike AFTER network events — proves root cause", "FHIR API 503 errors appear", "Active users drops sharply"] },
      { page: "Integration (/integration)", items: ["FHIR status shows 5xx spike", "HL7 delivery rate may dip (dependent on network path)", "FHIR response times go to timeout"] },
      { page: "Overview (/)", items: ["Epic↔Network Correlation: network drop precedes Epic drop", "KPIs: login rate drops, device up-ratio drops simultaneously"] }
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
    dtPages: [
      { page: "Integration (/integration)", items: ["HL7 delivery rate KPI drops to 0%", "HL7 volume timeline shows cliff, then flush burst on recovery", "Failed ETL jobs table populates (downstream impact)"] },
      { page: "Network Health (/network)", items: ["Access switch port CRC errors on VLAN 30", "Zero traffic on HL7 VLAN during err-disable", "Traffic burst when port comes back up"] },
      { page: "Epic Health (/epic)", items: ["Clinical orders show duplicates (staff re-entering due to missing results)", "Department Activity: lab/pharmacy departments impacted"] },
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
  "insider-threat-snooping": {
    icon: "🕵️",
    dtPages: [
      { page: "Epic Health (/epic)", items: ["Security Events: multiple AC_BREAK_THE_GLASS_ACCESS from single user", "SIEM Events: EXECUTIVE HEALTH department access from MED-SURG nurse", "After-hours activity (11PM-3AM) from single workstation IP"] },
      { page: "Security Page (NEW)", items: ["After-hours access heatmap shows anomalous window", "Break-the-glass count by user — one user far above normal", "VIP patient access audit trail"] },
      { page: "Overview (/)", items: ["Active users count shows late-night activity", "Low volume overall — this is a 'low and slow' attack"] }
    ],
    steps: [
      { title: "This one is subtle — start with Epic Health", text: "Security Events table shows break-the-glass events from one nurse during night shift. Multiple in one shift is unusual." },
      { title: "Look at the access pattern", text: "The nurse is accessing EXECUTIVE HEALTH department patients — completely outside their MED-SURG 3W scope. Name-based searches for coworkers." },
      { title: "Note the timing", text: "All activity between 11PM-3AM from a single workstation. This is deliberate after-hours snooping." },
      { title: "Show why this is hard to detect", text: "No network anomalies. No system errors. Normal volume. Only the PATTERN of access reveals the threat." }
    ],
    talking: [
      { icon: "🕵️", text: "Insider threats are the hardest to detect because they use legitimate credentials and normal access patterns." },
      { icon: "📋", text: "HIPAA: unauthorized access to PHI is a breach even if no data leaves the building. Each break-the-glass is auditable." },
      { icon: "🔑", text: "Detection requires behavioral analytics: WHO accessed WHAT, WHEN, and was it appropriate for their role?" }
    ]
  },
  "iomt-device-compromise": {
    icon: "💉",
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
    dtPages: [
      { page: "Epic Health (/epic)", items: ["Login failure rate spikes 500x normal", "Login success rate KPI drops sharply", "Security Events: FAILEDLOGIN, LOGIN_BLOCKED, WPSEC_LOGIN_FAIL flood"] },
      { page: "Network Health (/network)", items: ["NetFlow: distributed source IPs (botnet)", "External source countries bar chart shows unusual geography", "Citrix ADC connection count mirrors failure rate"] },
      { page: "MyChart View (NEW)", items: ["MyChart-specific login failure rate", "Patient portal action audit", "Successful stuffed logins → PHI access"] },
      { page: "Overview (/)", items: ["Login Success Rate KPI is the first indicator", "Active users count anomalous (includes bot sessions)"] }
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
      { icon: "🛡️", text: "Mitigations: rate limiting, MFA, CAPTCHA, WAF rules. F5 ASM detects and blocks the pattern." },
      { icon: "⚠️", text: "Even a 1.5% success rate = hundreds of compromised patient accounts. Each is a HIPAA breach." }
    ]
  }
};

async function loadScenarios() {
  const res = await fetch("/api/scenarios");
  const scenarios = await res.json();
  const grid = document.getElementById("scenario-selector");
  grid.innerHTML = scenarios.map(s => {
    const data = SCENARIO_DATA[s.key] || {};
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
  const data = SCENARIO_DATA[key];
  if (!data) return;

  // Update selector buttons
  document.querySelectorAll(".scenario-btn").forEach(b => b.classList.remove("active"));
  const activeBtn = document.querySelector(`[data-key="${key}"]`);
  if (activeBtn) activeBtn.classList.add("active");

  // Populate walkthrough
  document.getElementById("wt-icon").textContent = data.icon;
  // Get name from button text
  const nameEl = activeBtn?.querySelector(".scenario-btn-name");
  document.getElementById("wt-name").textContent = nameEl ? nameEl.textContent.slice(2).trim() : key;

  // Fetch scenario details for description and indicators
  fetch(`/api/scenarios`).then(r => r.json()).then(scenarios => {
    const s = scenarios.find(x => x.key === key);
    if (s) {
      document.getElementById("wt-desc").textContent = s.description;
      document.getElementById("wt-indicators").innerHTML = (s.indicators || []).map((ind, i) =>
        `<div class="indicator-item"><span class="indicator-num">${i+1}</span><span>${escHtml(ind)}</span></div>`
      ).join("") || '<p style="color:var(--text-muted)">Baseline scenario — no anomaly indicators.</p>';
    }
  });

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
