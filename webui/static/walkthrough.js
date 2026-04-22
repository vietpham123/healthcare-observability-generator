/* Scenario Walkthrough — Frontend Logic */
/* v2.3.0: 4 focused scenarios + baseline */

const DT_APP_URL = "https://gyz6507h.sprint.apps.dynatracelabs.com/ui/apps/my.dynatrace.healthcare.health.monitoring";

const SCENARIO_DATA = {
  "normal-day-shift": {
    icon: "\u{1f3e5}",
    prep: {
      activateMinsBefore: 5,
      totalRuntime: "Continuous (no fixed end)",
      summary: "Baseline scenario \u2014 runs continuously. Activate at least 5 minutes before the demo so the DT app has enough data points to render smooth time-series charts.",
      steps: [
        { when: "T-5 min", action: "Activate 'Normal Day Shift' from the Control Panel", why: "The generator needs ~3 ticks (30s) to start emitting logs, plus ~1-2 min for Dynatrace ingestion and indexing." },
        { when: "T-3 min", action: "Open the DT Healthcare app and navigate to Overview", why: "Verify data is flowing \u2014 you should see the System Activity timeline begin populating." },
        { when: "T-0", action: "Begin your demo", why: "You now have 5 min of baseline data showing normal curves \u2014 enough for the Overview, Epic Health, and Network charts to look realistic." }
      ],
      proTip: "For the best-looking demo, activate 15+ minutes before. Longer baseline = smoother time-series curves and more realistic time-of-day patterns."
    },
    dtPages: [
      { page: "Overview (/)", items: ["All KPIs green \u2014 login rate >98%, HL7 delivery 100%", "System Activity timeline shows steady volumes", "Campus map \u2014 all 4 sites reporting"] },
      { page: "Epic Health (/epic)", items: ["Login volume follows time-of-day curve (peak 10AM-2PM)", "Clinical orders show mix of STAT, Routine, PRN", "No security events beyond routine break-the-glass"] },
      { page: "Network (/network)", items: ["All 22 devices reporting (green hex tiles), CPU/mem in normal range", "Traffic patterns follow clinical schedule", "NetFlow \u2014 mostly internal, clinical protocols"] },
      { page: "Integration (/integration)", items: ["HL7 messages at steady 7AM-7PM rate", "FHIR API p95 <200ms, no errors", "ETL jobs completing on schedule", "Mirth Connect \u2014 all 5 channels running, zero queue depth"] }
    ],
    steps: [
      { title: "Show the Overview", text: "Point out all KPIs are green. The campus map shows all sites healthy. This is the baseline everything else deviates from." },
      { title: "Walk through Epic Health", text: "Show login volume follows a natural bell curve. Orders are a mix of types. Security events table is quiet \u2014 maybe 1-2 routine break-the-glass." },
      { title: "Check Network", text: "Device fleet honeycomb is all green (devices up). CPU and memory in normal range. Traffic is predictable." },
      { title: "Verify Integrations", text: "HL7, FHIR, ETL all green. Mirth Connect shows 5 channels with zero queue depth. This is the target state. Every scenario creates deviations FROM this baseline." }
    ],
    talking: [
      { icon: "\ud83d\udcca", text: "This is what 'normal' looks like \u2014 the baseline for anomaly detection." },
      { icon: "\ud83d\udd11", text: "Key: the DT app can spot deviations from this pattern across ALL subsystems simultaneously." },
      { icon: "\ud83d\udca1", text: "In a real hospital, these patterns change by shift (day vs night) and day of week. Our generator models these curves." }
    ]
  },

  "ransomware-attack": {
    icon: "\u{1f9a0}",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "60 min cycle (4 phases: Recon \u2192 Harvest \u2192 Lateral \u2192 Exfil)",
      summary: "Simulates a ransomware kill chain \u2014 phishing email at a satellite clinic compromises a workstation. Attacker pivots through WAN to main campus, harvests credentials against Epic, then begins mass patient record exfiltration. Correlated across Epic SIEM break-the-glass, login failures, and anomalous service audit events.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish baseline", why: "Login success rate needs to be at baseline (~83%) for the drop to be visible. Security page needs green KPIs." },
        { when: "T-10 min", action: "Switch to 'Ransomware Attack'", why: "Phase 1 (Recon) starts immediately \u2014 subtle probing. Within 5 min, Phase 2 (Harvest) begins with visible login failures." },
        { when: "T-5 min", action: "Verify Security page shows login failures climbing", why: "By now Epic Login Success % should be dropping toward AMBER. The attack is visibly underway." },
        { when: "T-0", action: "Begin demo \u2014 'We're seeing unusual login activity...'", why: "Security & Epic Health pages should be RED. The 4-phase kill chain is visible in the timeline." }
      ],
      proTip: "Let it run through all 4 phases (60 min) to show the complete kill chain. If time is short, the first 15 min covers Recon + Harvest which is enough to show Security and Epic Health going RED."
    },
    dtPages: [
      { page: "Security (/security)", items: ["Failed Logins spike from ~120 to 1400+ (RED)", "BTG events spike (credential testing triggers break-the-glass)", "Failed login source analysis shows concentrated activity", "Security events table fills with FAILEDLOGIN + BTG"] },
      { page: "Epic Health (/epic)", items: ["Login Success % drops from 83% to ~44% (RED)", "Login volume chart shows massive failure spike", "Service audit events from credential harvesting"] },
      { page: "Overview (/)", items: ["Epic Login Success KPI drops to RED", "System Activity shows event volume spike"] }
    ],
    steps: [
      { title: "Start at Overview \u2014 see the RED KPIs", text: "Epic Login Success KPI is RED. Something is very wrong with authentication." },
      { title: "Drill into Security", text: "Failed Logins have spiked to 1400+. BTG events are flooding in. The credential harvesting triggers break-the-glass events and the attack pattern is visible in the events table." },
      { title: "Check Epic Health", text: "Login Success Rate has dropped from 83% to below 45%. This is Phase 2 (Harvest) of the kill chain. The login trend chart shows the dramatic drop." },
      { title: "Return to Security for timeline", text: "Security Events Over Time chart shows the correlation \u2014 BTG and FAILEDLOGIN events spike together as the attack progresses through phases." },
      { title: "Explain the 4 phases", text: "Phase 1: Recon (subtle probing). Phase 2: Harvest (credential testing \u2014 what you see now). Phase 3: Lateral (moving through systems). Phase 4: Exfil (data extraction)." }
    ],
    talking: [
      { icon: "\u{1f9a0}", text: "Ransomware attacks on hospitals are real \u2014 they shut down clinical operations and endanger patients." },
      { icon: "\ud83d\udd11", text: "The kill chain has 4 phases. Real-time observability can detect Phase 1-2 before encryption begins." },
      { icon: "\u26a0\ufe0f", text: "Login failure spikes are the earliest detectable signal. Catching this in minutes vs hours saves the hospital." },
      { icon: "\ud83d\udcca", text: "The DT app correlates login failures + BTG events + service audits across the entire Epic ecosystem." }
    ]
  },

  "insider-threat-snooping": {
    icon: "\u{1f575}\ufe0f",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "50 min cycle",
      summary: "Night-shift nurse accesses VIP patient records, celebrity records, and coworker records outside their department. Low and slow \u2014 no network anomalies, only detectable via Epic SIEM patterns. This is a pure audit scenario.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish baseline BTG count", why: "BTG count needs to be low (baseline <200) for the spike to be clearly visible." },
        { when: "T-10 min", action: "Switch to 'Insider Threat'", why: "After-hours access begins \u2014 BTG events start climbing. Employee logs in, searches, accesses charts." },
        { when: "T-5 min", action: "Verify Security page shows BTG count climbing", why: "BTG count should be moving from GREEN toward AMBER. The pattern is building." },
        { when: "T-0", action: "Begin demo \u2014 'A privacy officer flagged unusual record access...'", why: "Security page should be RED (BTG count >400). The snooping pattern is clearly visible." }
      ],
      proTip: "This scenario is about behavioral detection, not volume. Emphasize that the access is 'low and slow' \u2014 no massive spikes, just a suspicious pattern over time."
    },
    dtPages: [
      { page: "Security (/security)", items: ["BTG Count spikes from <200 to >400 (RED)", "Break-the-glass events show after-hours timestamps", "Access pattern: VIP records, celebrity records, coworker records"] },
      { page: "Epic Health (/epic)", items: ["Login events show after-hours activity", "CHART_ACCESS events for patients outside user's department", "Event sequence: LOGIN \u2192 SEARCH \u2192 BTG \u2192 CHART_ACCESS"] },
      { page: "Overview (/)", items: ["BTG KPI turns RED", "No network impact \u2014 this is a pure Epic audit scenario"] }
    ],
    steps: [
      { title: "Start at Security \u2014 BTG count is RED", text: "Break-the-glass count has spiked well above the 400 threshold. Someone is accessing records they shouldn't." },
      { title: "Examine the access pattern", text: "The events show a sequence: LOGIN \u2192 SEARCH \u2192 BTG \u2192 CHART_ACCESS. This is an employee browsing records after hours." },
      { title: "Note: no network impact", text: "Network page is completely green. This is a pure behavioral anomaly \u2014 no malware, no network intrusion. Just an employee misusing access." },
      { title: "Discuss the HIPAA implications", text: "Every BTG event is an auditable access. This pattern \u2014 VIPs, celebrities, coworkers \u2014 is a textbook HIPAA violation." }
    ],
    talking: [
      { icon: "\u{1f575}\ufe0f", text: "Insider threats are the hardest to detect \u2014 legitimate credentials, no malware, no network anomalies." },
      { icon: "\u26a0\ufe0f", text: "Break-the-glass is designed for emergencies. Repeated BTG for non-emergency patients is a red flag." },
      { icon: "\ud83d\udcca", text: "Pattern detection: LOGIN at 2AM \u2192 SEARCH for VIP \u2192 BTG \u2192 CHART_ACCESS. The DT app surfaces this automatically." },
      { icon: "\ud83d\udee1\ufe0f", text: "This is a HIPAA audit scenario. The observability platform provides the evidence trail for compliance investigations." }
    ]
  },

  "hl7-interface-failure": {
    icon: "\u{1f50c}",
    prep: {
      activateMinsBefore: 10,
      totalRuntime: "Escalating \u2014 Mirth queue builds over time, FHIR/ETL errors compound",
      summary: "Switch port error on HL7 VLAN causes Mirth Connect queue backup. FHIR API errors spike to 65%, ETL jobs fail at 70%, HL7 message delivery stops. Integration page turns RED across all indicators. The escalating nature means the longer it runs, the worse it gets.",
      steps: [
        { when: "T-15 min (ideal)", action: "Run 'Normal Day Shift' to establish baseline integration metrics", why: "Integration page needs green KPIs \u2014 FHIR >85%, ETL >88%, HL7 >99%, Mirth queues at zero." },
        { when: "T-10 min", action: "Switch to 'HL7 Interface Failure'", why: "Mirth queue starts building, FHIR errors begin, ETL failures mount. The escalation takes 5-10 min to become dramatic." },
        { when: "T-5 min", action: "Check Integration page for degradation", why: "FHIR health should be dropping, Mirth queue depth climbing. ETL failures visible in the table." },
        { when: "T-0", action: "Begin demo \u2014 'Lab results aren't showing up in Epic...'", why: "Integration page should be RED. Mirth queue depth chart shows the escalating backup." }
      ],
      proTip: "Present as a help-desk ticket: 'Nurse calls: I ordered labs 2 hours ago and there are no results in Epic.' Then trace from clinical complaint to integration failure to network root cause."
    },
    dtPages: [
      { page: "Integration (/integration)", items: ["FHIR Health drops from 85% to ~35% (RED)", "ETL Success drops from 88% to ~30% (RED)", "HL7 Delivery Rate drops to 0% (RED)", "Mirth Connect queue depth chart shows escalating backup", "Mirth channel health drops below 80% (AMBER then RED)", "Failed ETL jobs table populates"] },
      { page: "Network (/network)", items: ["Access switch port errors on HL7 VLAN", "Reduced traffic on interface VLAN"] },
      { page: "Epic Health (/epic)", items: ["Service audit events from interface failures", "Clinical workflow disruption indicators"] },
      { page: "Overview (/)", items: ["Integration KPIs turn RED", "HL7 Delivery Rate is the most visible indicator"] }
    ],
    steps: [
      { title: "Start at Integration \u2014 everything is RED", text: "FHIR errors at 65%, ETL failing at 70%, HL7 delivery stopped. Mirth queue depth is climbing \u2014 the longer you wait, the worse it gets." },
      { title: "Focus on Mirth Connect", text: "The Mirth Connect section shows queue depth building for LAB-RESULTS-IN and ADT-OUT channels. Error rates spiking. Channels going from RUNNING to ERROR." },
      { title: "Trace to Network root cause", text: "Network page shows the switch port error on the HL7 VLAN. This single port failure cascaded to the entire integration engine." },
      { title: "Explain the escalation", text: "This is an escalating scenario \u2014 queue depth grows, errors compound. In a real hospital, this means no lab results, no radiology reports, no pharmacy orders flowing." }
    ],
    talking: [
      { icon: "\u{1f50c}", text: "HL7/Mirth interfaces are the nervous system of a hospital. A single switch port can stop all clinical data flow." },
      { icon: "\u26a0\ufe0f", text: "Clinical impact: no lab results, delayed radiology, pharmacy orders stuck. Clinicians start making decisions without complete data." },
      { icon: "\ud83d\udcc8", text: "The escalating Mirth queue is the key visual \u2014 it shows the problem getting worse over time, not just a binary up/down." },
      { icon: "\ud83d\udd17", text: "Integration observability + Network monitoring together pinpoint: it's not Epic, it's not Mirth \u2014 it's a network port on the HL7 VLAN." }
    ]
  },

  "core-switch-failure": {
    icon: "\u{1f525}",
    prep: {
      activateMinsBefore: 5,
      totalRuntime: "Continuous \u2014 core switch down, surviving infrastructure overloaded",
      summary: "Core network switch fails, causing device outages and increased load on remaining infrastructure. Epic systems experience intermittent connectivity \u2014 mild FHIR errors (15%) and ETL failures (20%) from network instability. Network page turns RED.",
      steps: [
        { when: "T-10 min (ideal)", action: "Run 'Normal Day Shift' to establish baseline", why: "Network page needs all devices UP and CPU <40% for the contrast to be visible." },
        { when: "T-5 min", action: "Switch to 'Core Switch Failure'", why: "Devices start going offline, surviving switches show CPU spikes. Impact is immediate." },
        { when: "T-2 min", action: "Verify Network page shows devices offline", why: "Device Up Ratio should be dropping. CPU chart should show spikes on surviving devices." },
        { when: "T-0", action: "Begin demo \u2014 'We lost a core switch...'", why: "Network page is RED. Device fleet shows offline devices. CPU is spiking." }
      ],
      proTip: "Good scenario for showing cascading failure \u2014 one switch down means remaining infrastructure is overloaded. Mention that Mirth shows mild degradation (30%) because some integration traffic routes through the failed switch."
    },
    dtPages: [
      { page: "Network (/network)", items: ["Device fleet honeycomb shows kcrmc-core-01 as RED (down)", "CPU spikes on kcrmc-dist-epic-01 (85%) and kcrmc-dist-epic-02 (78%)", "Device Up Ratio drops", "Traffic patterns disrupted"] },
      { page: "Integration (/integration)", items: ["Mild FHIR error increase (~15%)", "Mild ETL failure increase (~20%)", "Mirth shows slight degradation (30% error bump)", "Integration stays AMBER, not RED \u2014 secondary impact"] },
      { page: "Overview (/)", items: ["Network KPIs turn RED", "Integration KPIs may turn AMBER (mild cross-impact)"] }
    ],
    steps: [
      { title: "Start at Network \u2014 devices are offline", text: "Device Up Ratio has dropped below 95%. Some devices are unreachable. CPU on surviving switches is spiking as they handle rerouted traffic." },
      { title: "Show the cascading effect", text: "Surviving infrastructure is overloaded. CPU >60% means these switches are at risk too. This is a cascading failure pattern." },
      { title: "Check Integration for secondary impact", text: "Mild FHIR errors and ETL failures \u2014 not catastrophic, but noticeable. Some clinical data flow is disrupted by the network instability." },
      { title: "Contrast with HL7 Interface Failure", text: "Core Switch Failure \u2192 Network page RED, Integration AMBER. HL7 Failure \u2192 Integration page RED, Network mild. Different root cause, different primary impact." }
    ],
    talking: [
      { icon: "\u{1f525}", text: "Core switch failure is one of the most impactful network events \u2014 it affects everything that routes through it." },
      { icon: "\ud83d\udcca", text: "The key metric is Device Up Ratio \u2014 when it drops, you know you've lost infrastructure, not just a single link." },
      { icon: "\u26a1", text: "Surviving devices spike in CPU as they absorb rerouted traffic. This is the cascading failure pattern." },
      { icon: "\ud83d\udd17", text: "Cross-domain correlation: Network page RED \u2192 check Integration for secondary impact. The DT app connects the dots." }
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
