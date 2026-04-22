/* ══════════════════════════════════════════════════════════════
   DPS Discovery Questionnaire — JavaScript Engine
   ══════════════════════════════════════════════════════════════ */

const TOTAL_SECTIONS = 7;

/* ── Critical questions that most affect quote accuracy ─────── */
const CRITICAL_QUESTIONS = [
  { key: 'staffed_beds', label: 'Staffed Beds' },
  { key: 'daily_encounters', label: 'Daily Encounters' },
  { key: 'siem_audit_level', label: 'Audit Logging Level' },
  { key: 'managed_devices', label: 'Managed Network Devices' },
  { key: 'firewalls', label: 'Firewall Count' },
  { key: 'netflow_enabled', label: 'NetFlow Enabled?' },
  { key: 'syslog_verbosity', label: 'Syslog Verbosity' },
  { key: 'log_retention', label: 'Log Retention Period' },
];

/* ── Gold data points — direct measurements that bypass estimation ── */
const GOLD_QUESTIONS = [
  { key: 'current_ingest_gib', label: 'Current SIEM Ingest (GiB/day)' },
  { key: 'current_syslog_gib', label: 'Current Syslog Volume (GiB/day)' },
  { key: 'hl7_daily_volume', label: 'Daily HL7 Message Volume' },
];

/* ── All questions with scoring weight ──────────────────────── */
const QUESTIONS = [
  /* Section 1 — Organization Profile */
  { key: 'org_name',          section: 1, type: 'text',     weight: 1, label: 'Organization Name' },
  { key: 'org_type',          section: 1, type: 'radio',    weight: 3, label: 'Organization Type' },
  { key: 'staffed_beds',      section: 1, type: 'number',   weight: 5, label: 'Staffed Beds' },
  { key: 'daily_encounters',  section: 1, type: 'number',   weight: 5, label: 'Daily Encounters' },
  { key: 'num_facilities',    section: 1, type: 'number',   weight: 3, label: 'Number of Facilities' },
  { key: 'annual_revenue',    section: 1, type: 'select',   weight: 1, label: 'Annual Revenue' },
  /* Section 2 — EHR & Clinical */
  { key: 'ehr_vendor',            section: 2, type: 'radio',    weight: 4, label: 'EHR Vendor' },
  { key: 'peak_concurrent_users', section: 2, type: 'number',   weight: 3, label: 'Peak Concurrent Users' },
  { key: 'epic_modules',          section: 2, type: 'checkbox', weight: 3, label: 'EHR Modules' },
  { key: 'siem_audit_level',      section: 2, type: 'radio',    weight: 8, label: 'Audit Logging Level' },
  { key: 'mychart_active',        section: 2, type: 'number',   weight: 3, label: 'MyChart Active Users' },
  { key: 'existing_siem',         section: 2, type: 'checkbox', weight: 2, label: 'Current SIEM Platform' },
  { key: 'current_ingest_gib',    section: 2, type: 'number',   weight: 10, label: 'Current Ingest (GiB/day)' },
  /* Section 3 — Integration */
  { key: 'integration_engine',      section: 3, type: 'radio',  weight: 2, label: 'Integration Engine' },
  { key: 'active_channels',         section: 3, type: 'number', weight: 3, label: 'Active Channels' },
  { key: 'hl7_interfaces',          section: 3, type: 'number', weight: 3, label: 'HL7 Interfaces' },
  { key: 'hl7_daily_volume',        section: 3, type: 'number', weight: 5, label: 'HL7 Daily Volume' },
  { key: 'fhir_enabled',            section: 3, type: 'radio',  weight: 2, label: 'FHIR API Usage' },
  { key: 'care_everywhere_partners', section: 3, type: 'number', weight: 2, label: 'HIE Partners' },
  { key: 'etl_jobs',                section: 3, type: 'number', weight: 1, label: 'ETL Jobs' },
  /* Section 4 — Network */
  { key: 'managed_devices',   section: 4, type: 'number', weight: 5, label: 'Managed Devices' },
  { key: 'firewalls',         section: 4, type: 'number', weight: 5, label: 'Firewalls' },
  { key: 'firewall_vendor',   section: 4, type: 'radio',  weight: 2, label: 'Firewall Vendor' },
  { key: 'syslog_verbosity',  section: 4, type: 'radio',  weight: 6, label: 'Syslog Verbosity' },
  { key: 'netflow_enabled',   section: 4, type: 'radio',  weight: 7, label: 'NetFlow Enabled?' },
  { key: 'netflow_sampling',  section: 4, type: 'select', weight: 4, label: 'NetFlow Sampling Rate' },
  { key: 'snmp_polling',      section: 4, type: 'radio',  weight: 3, label: 'SNMP Polling Interval' },
  { key: 'current_syslog_gib', section: 4, type: 'number', weight: 8, label: 'Current Syslog (GiB/day)' },
  /* Section 5 — Security & Compliance */
  { key: 'compliance_frameworks',  section: 5, type: 'checkbox', weight: 2, label: 'Compliance Frameworks' },
  { key: 'log_retention',          section: 5, type: 'radio',   weight: 6, label: 'Log Retention Period' },
  { key: 'btg_frequency',          section: 5, type: 'radio',   weight: 1, label: 'Break-the-Glass Active' },
  { key: 'insider_threat_program', section: 5, type: 'radio',   weight: 2, label: 'Insider Threat Program' },
  /* Section 6 — Observability Goals */
  { key: 'dt_use_cases',    section: 6, type: 'checkbox', weight: 3, label: 'Use Cases in Scope' },
  { key: 'phased_rollout',  section: 6, type: 'radio',   weight: 2, label: 'Deployment Approach' },
  { key: 'dps_rate',        section: 6, type: 'number',   weight: 0, label: 'DPS Rate ($/DPS/month)' },
  { key: 'notes',           section: 6, type: 'textarea', weight: 0, label: 'Additional Notes' },
];

/* ── Section Navigation ────────────────────────────────────── */

function goToSection(num) {
  for (let i = 1; i <= TOTAL_SECTIONS; i++) {
    const el = document.getElementById(`section-${i}`);
    if (el) el.style.display = i === num ? '' : 'none';
  }
  /* Update tabs */
  document.querySelectorAll('.section-tab').forEach(tab => {
    const s = parseInt(tab.dataset.section, 10);
    tab.classList.toggle('active', s === num);
    tab.classList.toggle('visited', s < num);
  });
  /* Update progress */
  const pct = Math.round((num / TOTAL_SECTIONS) * 100);
  const fill = document.getElementById('progress-fill');
  const label = document.getElementById('progress-label');
  if (fill) fill.style.width = `${pct}%`;
  if (label) label.textContent = `Section ${num} of ${TOTAL_SECTIONS}`;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── Collect Answers ───────────────────────────────────────── */

function collectAnswers() {
  const answers = {};

  QUESTIONS.forEach(q => {
    const section = document.getElementById(`section-${q.section}`);
    if (!section) return;
    const group = section.querySelector(`[data-key="${q.key}"]`);
    if (!group) return;

    if (q.type === 'text' || q.type === 'number') {
      const inp = group.querySelector('input.q-input, input.q-number');
      if (inp && inp.value.trim() !== '') {
        answers[q.key] = q.type === 'number' ? parseFloat(inp.value) : inp.value.trim();
      }
    } else if (q.type === 'textarea') {
      const ta = group.querySelector('textarea');
      if (ta && ta.value.trim() !== '') {
        answers[q.key] = ta.value.trim();
      }
    } else if (q.type === 'select') {
      const sel = group.querySelector('select');
      if (sel && sel.value !== '') {
        answers[q.key] = sel.value;
      }
    } else if (q.type === 'radio') {
      const checked = group.querySelector(`input[name="${q.key}"]:checked`);
      if (checked) {
        answers[q.key] = checked.value;
      }
    } else if (q.type === 'checkbox') {
      const checked = group.querySelectorAll('input[type="checkbox"]:checked');
      if (checked.length > 0) {
        answers[q.key] = Array.from(checked).map(cb => {
          /* Try data-module, data-siem, data-fw, data-uc, then value */
          return cb.dataset.module || cb.dataset.siem || cb.dataset.fw || cb.dataset.uc || cb.value;
        });
      }
    }
  });
  return answers;
}

/* ── Confidence Score ──────────────────────────────────────── */

function calculateConfidence(answers) {
  let earned = 0;
  let total = 0;

  QUESTIONS.forEach(q => {
    if (q.weight === 0) return;
    total += q.weight;
    if (answers[q.key] !== undefined) {
      earned += q.weight;
    }
  });

  /* Gold data bonus — direct measurements add extra confidence */
  GOLD_QUESTIONS.forEach(g => {
    if (answers[g.key] !== undefined && answers[g.key] > 0) {
      earned += 5; /* bonus points for real data */
      total += 5;
    } else {
      total += 5;
    }
  });

  return Math.min(100, Math.round((earned / total) * 100));
}

function getConfidenceLevel(score) {
  if (score >= 85) return { label: 'High Confidence', color: '#4ade80', desc: 'Sufficient data for an accurate quote. Sizing estimates should be within ±20% of actual.' };
  if (score >= 65) return { label: 'Moderate Confidence', color: '#fbbf24', desc: 'Key data collected, but some critical gaps remain. Sizing estimates may be within ±40%. Recommend resolving gaps before quoting.' };
  if (score >= 40) return { label: 'Low Confidence', color: '#f97316', desc: 'Significant gaps in discovery data. Quote accuracy may vary by ±60% or more. Additional discovery recommended before formal quoting.' };
  return { label: 'Insufficient Data', color: '#ef4444', desc: 'Not enough data for a reliable quote. Recommend completing at least Sections 1–4 before proceeding.' };
}

/* ── Generate Summary ──────────────────────────────────────── */

function generateSummary() {
  const answers = collectAnswers();
  const confidence = calculateConfidence(answers);
  const level = getConfidenceLevel(confidence);

  /* Confidence Panel */
  const scoreEl = document.getElementById('confidence-score');
  const barEl = document.getElementById('confidence-bar');
  const descEl = document.getElementById('confidence-desc');
  if (scoreEl) scoreEl.textContent = `${confidence}%`;
  if (scoreEl) scoreEl.style.color = level.color;
  if (barEl) { barEl.style.width = `${confidence}%`; barEl.style.background = level.color; }
  if (descEl) descEl.textContent = `${level.label} — ${level.desc}`;

  /* Critical Gaps */
  renderGaps(answers);

  /* Summary Grid */
  renderSummaryGrid(answers);

  /* Sizing Guidance */
  renderSizingGuidance(answers);

  /* Next Steps */
  renderNextSteps(answers, confidence);
}

function renderGaps(answers) {
  const gapsList = document.getElementById('gaps-list');
  const gapsPanel = document.getElementById('gaps-panel');
  if (!gapsList || !gapsPanel) return;

  const gaps = [];
  CRITICAL_QUESTIONS.forEach(cq => {
    if (answers[cq.key] === undefined) {
      gaps.push(cq.label);
    }
  });

  if (gaps.length === 0) {
    gapsPanel.style.display = 'none';
  } else {
    gapsPanel.style.display = '';
    gapsList.innerHTML = gaps.map(g => `<li>${g}</li>`).join('');
  }
}

function renderSummaryGrid(answers) {
  const grid = document.getElementById('summary-grid');
  if (!grid) return;

  let html = '';
  let currentSection = 0;
  QUESTIONS.forEach(q => {
    if (q.section !== currentSection) {
      currentSection = q.section;
      const sectionNames = ['', 'Organization', 'EHR & Clinical', 'Integration', 'Network', 'Security & Compliance', 'Observability Goals'];
      html += `<div class="summary-section-header">${sectionNames[currentSection]}</div>`;
    }
    const val = answers[q.key];
    const display = val === undefined ? '<span class="gap">—</span>' : formatValue(q.key, val);
    const cls = val === undefined ? 'summary-item unanswered' : 'summary-item answered';
    html += `<div class="${cls}"><span class="s-label">${q.label}</span><span class="s-value">${display}</span></div>`;
  });
  grid.innerHTML = html;
}

function formatValue(key, val) {
  if (Array.isArray(val)) return val.join(', ');
  if (typeof val === 'number') {
    if (key.includes('gib') || key === 'dps_rate') return val.toLocaleString() + (key.includes('gib') ? ' GiB/day' : '');
    return val.toLocaleString();
  }
  /* Capitalize known codes */
  const maps = {
    community: 'Community Hospital', regional: 'Regional Medical Center', academic: 'Academic Medical Center',
    health_system: 'Multi-Hospital System', critical_access: 'Critical Access', specialty: 'Specialty/Children\'s',
    epic: 'Epic', cerner: 'Oracle Health (Cerner)', meditech: 'MEDITECH', other: 'Other',
    low: 'Minimal', medium: 'Standard', high: 'Verbose', custom: 'Extended/Regulatory',
    errors: 'Errors Only', warnings: 'Warnings + Errors', informational: 'Informational', debug: 'Debug',
    no: 'No', yes: 'Yes', limited: 'Limited', active: 'Active', planned: 'Planned',
    sampled: 'Yes — Sampled', full: 'Yes — Full (1:1)', unknown: 'Unknown',
    all_at_once: 'Big Bang', phased: 'Phased', poc: 'POC First',
    mirth: 'Mirth Connect', rhapsody: 'Rhapsody', cloverleaf: 'Cloverleaf', bridges: 'Epic Bridges', ensemble: 'InterSystems',
    palo_alto: 'Palo Alto', fortinet: 'Fortinet', cisco: 'Cisco ASA/FTD', checkpoint: 'Check Point', sophos: 'Sophos',
    under_100m: '<$100M', '100m_500m': '$100M–$500M', '500m_1b': '$500M–$1B', '1b_5b': '$1B–$5B', over_5b: '>$5B',
  };
  return maps[val] || val;
}

function renderSizingGuidance(answers) {
  const container = document.getElementById('sizing-recommendations');
  if (!container) return;

  const recs = [];

  /* Log ingest estimate */
  const beds = answers.staffed_beds || 0;
  const encounters = answers.daily_encounters || 0;
  const devices = answers.managed_devices || 0;
  const firewalls = answers.firewalls || 0;
  const auditLevel = answers.siem_audit_level || 'medium';
  const syslogLevel = answers.syslog_verbosity || 'warnings';
  const netflowEnabled = answers.netflow_enabled || 'no';
  const netflowSampling = parseInt(answers.netflow_sampling || '100', 10);
  const retention = parseInt(answers.log_retention || '90', 10);

  /* Audit multiplier */
  const auditMultiplier = { low: 0.3, medium: 1, high: 3, custom: 5 }[auditLevel] || 1;
  /* Syslog multiplier */
  const syslogMultiplier = { errors: 0.1, warnings: 1, informational: 5, debug: 20 }[syslogLevel] || 1;

  /* SIEM estimate (GiB/day) */
  if (beds > 0) {
    const siemEventsPerDay = beds * 15000 * auditMultiplier; /* midpoint base */
    const siemGiB = (siemEventsPerDay * 0.5) / (1024 * 1024 * 1024); /* ~500 bytes/event */
    recs.push({ source: 'Epic SIEM / Audit', lowGiB: siemGiB * 0.6, highGiB: siemGiB * 1.8, notes: `${beds} beds × ${auditLevel} audit` });
  }

  /* Clinical events */
  if (encounters > 0) {
    const clinGiB = (encounters * 18 * 0.8) / (1024 * 1024); /* 18 events/encounter, 800 bytes avg */
    recs.push({ source: 'Clinical Events', lowGiB: clinGiB * 0.6, highGiB: clinGiB * 1.5, notes: `${encounters} encounters/day` });
  }

  /* HL7 */
  const hl7Ifaces = answers.hl7_interfaces || 0;
  if (hl7Ifaces > 0) {
    const hl7MsgsLow = hl7Ifaces * 800;
    const hl7MsgsHigh = hl7Ifaces * 3000;
    recs.push({ source: 'HL7v2 Messages', lowGiB: (hl7MsgsLow * 1500) / (1024*1024*1024), highGiB: (hl7MsgsHigh * 1500) / (1024*1024*1024), notes: `${hl7Ifaces} interfaces` });
  }

  /* Override with gold data if available */
  if (answers.hl7_daily_volume > 0) {
    const idx = recs.findIndex(r => r.source.includes('HL7'));
    if (idx >= 0) {
      const gib = (answers.hl7_daily_volume * 1500) / (1024*1024*1024);
      recs[idx] = { source: 'HL7v2 Messages ⭐', lowGiB: gib * 0.8, highGiB: gib * 1.2, notes: `${answers.hl7_daily_volume.toLocaleString()} msgs/day (measured)` };
    }
  }

  /* Network syslog */
  if (devices > 0) {
    const eventsPerDevice = 10000 * syslogMultiplier;
    const totalEvents = devices * eventsPerDevice;
    const gib = (totalEvents * 350) / (1024*1024*1024); /* 350 bytes avg */
    recs.push({ source: 'Network Syslog', lowGiB: gib * 0.5, highGiB: gib * 2.0, notes: `${devices} devices × ${syslogLevel}` });
  }

  /* Override with gold data */
  if (answers.current_syslog_gib > 0) {
    const idx = recs.findIndex(r => r.source.includes('Syslog'));
    if (idx >= 0) {
      recs[idx] = { source: 'Network Syslog ⭐', lowGiB: answers.current_syslog_gib * 0.9, highGiB: answers.current_syslog_gib * 1.1, notes: `${answers.current_syslog_gib} GiB/day (measured)` };
    }
  }

  /* NetFlow */
  if (firewalls > 0 && netflowEnabled !== 'no') {
    const baseFlows = firewalls * 10000000; /* 10M flows/fw/day at 1:1 */
    const sampledFlows = baseFlows / (netflowSampling || 100);
    const gib = (sampledFlows * 400) / (1024*1024*1024); /* 400 bytes/record */
    recs.push({ source: 'NetFlow / IPFIX', lowGiB: gib * 0.5, highGiB: gib * 2.0, notes: `${firewalls} FW, 1:${netflowSampling} sampling` });
  }

  /* MyChart */
  if (answers.mychart_active > 0) {
    const evts = answers.mychart_active * 5; /* 5 events/user/day midpoint */
    const gib = (evts * 700) / (1024*1024*1024);
    recs.push({ source: 'MyChart / Patient Portal', lowGiB: gib * 0.5, highGiB: gib * 3.0, notes: `${answers.mychart_active.toLocaleString()} active users/month` });
  }

  /* Mirth metrics */
  const channels = answers.active_channels || 0;
  if (channels > 0) {
    const ddus = channels * 8640; /* 6 metrics × 1440 min/day */
    recs.push({ source: 'Mirth Metrics (DDUs)', lowGiB: null, highGiB: null, ddus: ddus, notes: `${channels} channels × 1-min poll` });
  }

  /* SNMP metrics */
  if (devices > 0 && answers.snmp_polling && answers.snmp_polling !== 'none') {
    const interval = parseInt(answers.snmp_polling, 10);
    const pollsPerDay = 86400 / interval;
    const metricsPerPoll = 15; /* typical OIDs per device */
    const ddus = devices * pollsPerDay * metricsPerPoll;
    recs.push({ source: 'SNMP Metrics (DDUs)', lowGiB: null, highGiB: null, ddus: ddus, notes: `${devices} devices @ ${interval}s interval` });
  }

  /* Render */
  if (recs.length === 0) {
    container.innerHTML = '<p class="gap">Not enough data to generate sizing guidance. Complete Sections 1–4.</p>';
    return;
  }

  let totalLow = 0, totalHigh = 0, totalDDUs = 0;
  let html = '<table class="sizing-table"><thead><tr><th>Data Source</th><th>Low Est.</th><th>High Est.</th><th>Notes</th></tr></thead><tbody>';
  recs.forEach(r => {
    if (r.ddus) {
      totalDDUs += r.ddus;
      html += `<tr><td>${r.source}</td><td colspan="2" style="text-align:center">${(r.ddus/1000).toFixed(0)}K DDUs/day</td><td>${r.notes}</td></tr>`;
    } else {
      totalLow += r.lowGiB;
      totalHigh += r.highGiB;
      html += `<tr><td>${r.source}</td><td>${r.lowGiB.toFixed(1)} GiB</td><td>${r.highGiB.toFixed(1)} GiB</td><td>${r.notes}</td></tr>`;
    }
  });

  html += `<tr class="total-row"><td><strong>Total Log Ingest</strong></td><td><strong>${totalLow.toFixed(1)} GiB/day</strong></td><td><strong>${totalHigh.toFixed(1)} GiB/day</strong></td><td></td></tr>`;
  if (totalDDUs > 0) {
    html += `<tr class="total-row"><td><strong>Total Metric DDUs</strong></td><td colspan="2" style="text-align:center"><strong>${(totalDDUs/1000).toFixed(0)}K DDUs/day</strong></td><td></td></tr>`;
  }

  /* Override with gold data */
  if (answers.current_ingest_gib > 0) {
    html += `<tr class="gold-row"><td>⭐ Customer-Reported Ingest</td><td colspan="2" style="text-align:center"><strong>${answers.current_ingest_gib} GiB/day</strong></td><td>Direct measurement — use this as primary baseline</td></tr>`;
  }

  /* DPS estimate */
  const ingestGiB = answers.current_ingest_gib > 0 ? answers.current_ingest_gib : (totalLow + totalHigh) / 2;
  const dpsIngest = ingestGiB * 1.0;
  const dpsStorage = ingestGiB * retention * 0.0035;
  const dpsMetrics = (totalDDUs / 1000) * 0.001;
  const dpsTotalLow = (totalLow * 1.0) + (totalLow * retention * 0.0035) + dpsMetrics;
  const dpsTotalHigh = (totalHigh * 1.0) + (totalHigh * retention * 0.0035) + dpsMetrics;

  html += `</tbody></table>`;
  html += `<div class="dps-estimate">`;
  html += `<h4>Preliminary DPS Range</h4>`;
  html += `<div class="dps-range">`;
  html += `<div class="dps-val"><span class="dps-num">${dpsTotalLow.toFixed(1)}</span><span class="dps-label">Low DPS</span></div>`;
  html += `<span class="dps-dash">—</span>`;
  html += `<div class="dps-val"><span class="dps-num">${dpsTotalHigh.toFixed(1)}</span><span class="dps-label">High DPS</span></div>`;
  html += `</div>`;
  html += `<p class="dps-breakdown">Ingest: ${dpsIngest.toFixed(1)} DPS · Storage (${retention}d): ${dpsStorage.toFixed(1)} DPS · Metrics: ${dpsMetrics.toFixed(2)} DPS</p>`;

  if (answers.dps_rate > 0) {
    const costLow = dpsTotalLow * answers.dps_rate;
    const costHigh = dpsTotalHigh * answers.dps_rate;
    html += `<p class="dps-cost">Estimated Monthly: $${costLow.toLocaleString(undefined, {maximumFractionDigits:0})} – $${costHigh.toLocaleString(undefined, {maximumFractionDigits:0})} at $${answers.dps_rate}/DPS/mo</p>`;
  }
  html += `</div>`;

  container.innerHTML = html;
}

function renderNextSteps(answers, confidence) {
  const list = document.getElementById('next-steps');
  if (!list) return;

  const steps = [];

  /* Always suggest filling critical gaps */
  CRITICAL_QUESTIONS.forEach(cq => {
    if (answers[cq.key] === undefined) {
      steps.push(`<strong>Collect:</strong> ${cq.label} — This is a critical data point for accurate sizing.`);
    }
  });

  /* Gold data collection */
  GOLD_QUESTIONS.forEach(g => {
    if (answers[g.key] === undefined || answers[g.key] === 0) {
      steps.push(`<strong>Ask for:</strong> ${g.label} — Direct measurements dramatically improve accuracy.`);
    }
  });

  /* Cross-validation suggestions */
  if (answers.staffed_beds && answers.peak_concurrent_users) {
    const expectedUsers = answers.staffed_beds * 0.8;
    if (answers.peak_concurrent_users > expectedUsers * 2) {
      steps.push(`<strong>Validate:</strong> Peak users (${answers.peak_concurrent_users}) seems high for ${answers.staffed_beds} beds. Confirm with customer.`);
    }
  }

  if (answers.siem_audit_level === 'high' || answers.siem_audit_level === 'custom') {
    steps.push(`<strong>Verify:</strong> Verbose/extended audit logging has a massive impact (3–8×). Double-check this with the Epic team.`);
  }

  if (answers.netflow_enabled === 'full') {
    steps.push(`<strong>⚠️ Flag:</strong> Full 1:1 NetFlow can generate 10–50× more data than sampled. Confirm this is intentional and discuss sampling as a cost optimization.`);
  }

  /* Standard next steps */
  if (confidence >= 65) {
    steps.push(`Feed these inputs into the <a href="/pricing">DPS Calculator</a> for detailed subsystem-level estimates.`);
    steps.push(`Prepare a formal quote document with low/mid/high ranges and share with the customer for validation.`);
  }
  if (confidence < 65) {
    steps.push(`Schedule a follow-up discovery call focused on the gaps identified above.`);
  }
  steps.push(`Review with Dynatrace pricing team before finalizing quote.`);

  list.innerHTML = steps.map(s => `<li>${s}</li>`).join('');
}

/* ── Export Functions ───────────────────────────────────────── */

function exportDiscovery() {
  const answers = collectAnswers();
  const confidence = calculateConfidence(answers);
  const payload = {
    exportDate: new Date().toISOString(),
    confidence: confidence,
    confidenceLevel: getConfidenceLevel(confidence).label,
    answers: answers,
    criticalGaps: CRITICAL_QUESTIONS.filter(cq => answers[cq.key] === undefined).map(cq => cq.label),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `dps-discovery-${(answers.org_name || 'unnamed').replace(/\s+/g, '-').toLowerCase()}-${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportDiscoveryCSV() {
  const answers = collectAnswers();
  let csv = 'Question,Answer\n';
  QUESTIONS.forEach(q => {
    const val = answers[q.key];
    const display = val === undefined ? '' : (Array.isArray(val) ? val.join('; ') : String(val));
    csv += `"${q.label}","${display.replace(/"/g, '""')}"\n`;
  });
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `dps-discovery-${(answers.org_name || 'unnamed').replace(/\s+/g, '-').toLowerCase()}-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function copyToClipboard() {
  const answers = collectAnswers();
  const confidence = calculateConfidence(answers);
  const level = getConfidenceLevel(confidence);

  let text = `DPS Discovery Summary\n`;
  text += `Date: ${new Date().toLocaleDateString()}\n`;
  text += `Confidence: ${confidence}% (${level.label})\n\n`;

  let currentSection = 0;
  const sectionNames = ['', 'Organization', 'EHR & Clinical', 'Integration', 'Network', 'Security & Compliance', 'Observability Goals'];
  QUESTIONS.forEach(q => {
    if (q.section !== currentSection) {
      currentSection = q.section;
      text += `\n--- ${sectionNames[currentSection]} ---\n`;
    }
    const val = answers[q.key];
    const display = val === undefined ? '(not answered)' : (Array.isArray(val) ? val.join(', ') : formatValue(q.key, val));
    text += `${q.label}: ${display}\n`;
  });

  /* Gaps */
  const gaps = CRITICAL_QUESTIONS.filter(cq => answers[cq.key] === undefined);
  if (gaps.length > 0) {
    text += `\n--- Critical Gaps ---\n`;
    gaps.forEach(g => { text += `• ${g.label}\n`; });
  }

  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('[onclick="copyToClipboard()"]');
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = '✅ Copied!';
      setTimeout(() => { btn.textContent = orig; }, 2000);
    }
  });
}
