/* Healthcare DPS Pricing Estimator — Calculator Engine
 *
 * Volume formulas are parametric estimates based on:
 *   - Epic Systems published infrastructure sizing guidance
 *   - CHIME Digital Health benchmarks for hospital IT
 *   - Industry-standard syslog/NetFlow volume analysis
 *   - Mirth Connect channel throughput documentation
 *
 * All estimates produce LOW–HIGH ranges (±30% variance).
 * DPS conversion rates are illustrative unless user provides contract rate.
 */

// ── Wizard Navigation ────────────────────────────────────────────

let currentStep = 1;

function goToStep(step) {
  document.querySelectorAll('.wizard-panel').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.wizard-step').forEach(s => {
    s.classList.toggle('active', parseInt(s.dataset.step) <= step);
    s.classList.toggle('current', parseInt(s.dataset.step) === step);
  });
  document.getElementById(`step-${step}`).style.display = '';
  currentStep = step;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function calculateAndShow() {
  const results = calculate();
  renderResults(results);
  goToStep(4);
}

// ── Slider Binding ───────────────────────────────────────────────

function fmt(n) {
  return n.toLocaleString('en-US');
}

document.querySelectorAll('input[type="range"]').forEach(slider => {
  const display = document.getElementById(slider.id + '-val');
  if (display) {
    display.textContent = fmt(parseInt(slider.value));
    slider.addEventListener('input', () => {
      display.textContent = fmt(parseInt(slider.value));
    });
  }
});

// ── Volume Constants (per-unit-per-day baselines) ────────────────
// These are derived from healthcare IT industry benchmarks.
// Each constant has a LOW and HIGH range.

const VOLUME = {
  // ── Epic SIEM Audit ──
  // Events per staffed bed per day, by audit level
  siem: {
    low:    { perBed: 4000,  perUser: 800  },  // Login/logout only
    medium: { perBed: 10000, perUser: 2000 },  // Standard clinical audit
    high:   { perBed: 30000, perUser: 5000 },  // Verbose all-access audit
    custom: { perBed: 40000, perUser: 8000 },  // SOX/HIPAA extended
    avgSizeBytes: 850,  // Average SIEM XML event size
    moduleMultiplier: 0.08, // Each additional module adds ~8% to SIEM volume
  },

  // ── Clinical Events (Orders, Meds, Notes, Results, Flowsheets) ──
  clinical: {
    perEncounter: { low: 12, high: 25 },  // Clinical events per encounter
    avgSizeBytes: 1200,
  },

  // ── HL7v2 Messages ──
  hl7: {
    perInterface: { low: 800, high: 3000 },   // Messages per interface per day
    perEncounter: { low: 4, high: 12 },        // Messages per encounter
    avgSizeBytes: 1500,
  },

  // ── FHIR API ──
  fhir: {
    perUser: { low: 50, high: 200 },           // API calls per concurrent user per day
    perPartner: { low: 500, high: 5000 },      // Calls per Care Everywhere partner per day
    avgSizeBytes: 500,
  },

  // ── MyChart Portal ──
  mychart: {
    perActivePatient: { low: 0.5, high: 2.0 }, // Sessions per active patient per day
    eventsPerSession: { low: 3, high: 8 },      // Log events per session
    avgSizeBytes: 400,
  },

  // ── ETL / Integration Jobs ──
  etl: {
    perInterface: { low: 20, high: 80 },  // Job log records per interface per day
    avgSizeBytes: 600,
  },

  // ── Network Syslog ──
  syslog: {
    perDevice: {
      errors:        { low: 200,   high: 800   },
      warnings:      { low: 2000,  high: 8000  },
      informational: { low: 10000, high: 30000 },
      debug:         { low: 50000, high: 200000},
    },
    perFirewall: {  // Firewalls generate 3-10× more logs than switches
      errors:        { low: 1000,   high: 5000   },
      warnings:      { low: 10000,  high: 40000  },
      informational: { low: 50000,  high: 150000 },
      debug:         { low: 200000, high: 800000 },
    },
    avgSizeBytes: 300,
  },

  // ── NetFlow Records ──
  netflow: {
    // Records per firewall per day at 1:1 sampling
    perFirewallBase: { low: 5000000, high: 20000000 },
    avgSizeBytes: 400,
  },

  // ── Mirth Connect Metrics ──
  mirth: {
    metricsPerChannelPerDay: 8640,  // 6 metrics × 1440 min/day (1-min resolution)
    // Each metric line = 1 DDU (data point)
  },

  // ── Network Device Metrics (SNMP) ──
  snmp: {
    metricsPerDevicePerPoll: 6, // CPU, mem, 2× traffic (in/out), errors, uptime
    avgInterfacesPerDevice: 8,  // Average switchports/interfaces
    metricsPerInterfacePerPoll: 4, // traffic in, out, errors, discards
  },
};

// ── DPS Conversion Rates (illustrative) ──────────────────────────
// These are approximate and should be overridden with actual contract rates.

const DPS_RATES = {
  logIngestPerGiB: 1.0,         // ~1 DPS per GiB of log data ingested
  logStoragePerGiBDay: 0.0035,  // ~0.0035 DPS per GiB stored per day
  metricPer1000DDU: 0.001,      // ~0.001 DPS per 1000 metric data points
};

// ── Main Calculation ─────────────────────────────────────────────

function getInputs() {
  return {
    beds:            parseInt(document.getElementById('staffed-beds').value),
    encounters:      parseInt(document.getElementById('daily-encounters').value),
    peakUsers:       parseInt(document.getElementById('peak-epic-users').value),
    myChartPatients: parseInt(document.getElementById('mychart-patients').value),
    devices:         parseInt(document.getElementById('network-devices').value),
    firewalls:       parseInt(document.getElementById('firewalls').value),
    mirthChannels:   parseInt(document.getElementById('mirth-channels').value),
    hl7Interfaces:   parseInt(document.getElementById('hl7-interfaces').value),
    sites:           parseInt(document.getElementById('sites').value),
    cePartners:      parseInt(document.getElementById('care-everywhere-partners').value),
    auditLevel:      document.getElementById('siem-audit-level').value,
    netflowSampling: parseInt(document.getElementById('netflow-sampling').value),
    syslogLevel:     document.getElementById('syslog-level').value,
    snmpInterval:    parseInt(document.getElementById('snmp-poll-interval').value),
    retentionDays:   parseInt(document.getElementById('retention-days').value),
    dpsRate:         parseFloat(document.getElementById('dps-rate').value) || 0,
    epicModules:     document.querySelectorAll('.epic-module:checked').length,
  };
}

function calculate() {
  const i = getInputs();
  const subsystems = [];

  // ── 1. Epic SIEM Audit ──
  const siemProfile = VOLUME.siem[i.auditLevel] || VOLUME.siem.medium;
  const baseModules = 4; // Core modules always active
  const extraModules = Math.max(0, i.epicModules - baseModules);
  const moduleBoost = 1 + (extraModules * VOLUME.siem.moduleMultiplier);
  const siemFromBeds = siemProfile.perBed * i.beds;
  const siemFromUsers = siemProfile.perUser * i.peakUsers;
  const siemBase = Math.max(siemFromBeds, siemFromUsers) * moduleBoost;
  subsystems.push({
    name: 'Epic SIEM Audit',
    icon: '🔐',
    type: 'log',
    low:  Math.round(siemBase * 0.7),
    high: Math.round(siemBase * 1.3),
    avgSize: VOLUME.siem.avgSizeBytes,
    unit: 'events',
    methodology: `${fmt(siemProfile.perBed)} events/bed/day (${i.auditLevel} audit) × ${i.beds} beds × ${moduleBoost.toFixed(2)} module factor`,
  });

  // ── 2. Clinical Events ──
  const clinLow  = i.encounters * VOLUME.clinical.perEncounter.low;
  const clinHigh = i.encounters * VOLUME.clinical.perEncounter.high;
  subsystems.push({
    name: 'Clinical Events',
    icon: '📋',
    type: 'log',
    low: clinLow,
    high: clinHigh,
    avgSize: VOLUME.clinical.avgSizeBytes,
    unit: 'events',
    methodology: `${VOLUME.clinical.perEncounter.low}–${VOLUME.clinical.perEncounter.high} events/encounter × ${fmt(i.encounters)} encounters/day`,
  });

  // ── 3. HL7v2 Messages ──
  const hl7FromInterfaces = i.hl7Interfaces * avg(VOLUME.hl7.perInterface);
  const hl7FromEncounters = i.encounters * avg(VOLUME.hl7.perEncounter);
  const hl7Base = Math.max(hl7FromInterfaces, hl7FromEncounters);
  subsystems.push({
    name: 'HL7v2 Messages',
    icon: '🔌',
    type: 'log',
    low:  Math.round(hl7Base * 0.7),
    high: Math.round(hl7Base * 1.3),
    avgSize: VOLUME.hl7.avgSizeBytes,
    unit: 'messages',
    methodology: `max(${fmt(Math.round(hl7FromInterfaces))} from ${i.hl7Interfaces} interfaces, ${fmt(Math.round(hl7FromEncounters))} from ${fmt(i.encounters)} encounters)`,
  });

  // ── 4. FHIR API ──
  const fhirFromUsers = i.peakUsers * avg(VOLUME.fhir.perUser);
  const fhirFromPartners = i.cePartners * avg(VOLUME.fhir.perPartner);
  const fhirTotal = fhirFromUsers + fhirFromPartners;
  subsystems.push({
    name: 'FHIR / Interconnect API',
    icon: '🔗',
    type: 'log',
    low:  Math.round(fhirTotal * 0.7),
    high: Math.round(fhirTotal * 1.3),
    avgSize: VOLUME.fhir.avgSizeBytes,
    unit: 'calls',
    methodology: `${fmt(Math.round(fhirFromUsers))} from ${i.peakUsers} users + ${fmt(Math.round(fhirFromPartners))} from ${i.cePartners} CE partners`,
  });

  // ── 5. MyChart ──
  const dailyMyChart = i.myChartPatients / 30; // Monthly → daily active
  const myChartEventsLow  = dailyMyChart * VOLUME.mychart.perActivePatient.low * VOLUME.mychart.eventsPerSession.low;
  const myChartEventsHigh = dailyMyChart * VOLUME.mychart.perActivePatient.high * VOLUME.mychart.eventsPerSession.high;
  subsystems.push({
    name: 'MyChart Portal',
    icon: '📱',
    type: 'log',
    low:  Math.round(myChartEventsLow),
    high: Math.round(myChartEventsHigh),
    avgSize: VOLUME.mychart.avgSizeBytes,
    unit: 'events',
    methodology: `${fmt(Math.round(dailyMyChart))} daily active patients × ${VOLUME.mychart.perActivePatient.low}–${VOLUME.mychart.perActivePatient.high} sessions × ${VOLUME.mychart.eventsPerSession.low}–${VOLUME.mychart.eventsPerSession.high} events`,
  });

  // ── 6. ETL / Integration Jobs ──
  const etlLow  = i.hl7Interfaces * VOLUME.etl.perInterface.low;
  const etlHigh = i.hl7Interfaces * VOLUME.etl.perInterface.high;
  subsystems.push({
    name: 'ETL / Integration Jobs',
    icon: '🔄',
    type: 'log',
    low:  etlLow,
    high: etlHigh,
    avgSize: VOLUME.etl.avgSizeBytes,
    unit: 'records',
    methodology: `${VOLUME.etl.perInterface.low}–${VOLUME.etl.perInterface.high} records/interface × ${i.hl7Interfaces} interfaces`,
  });

  // ── 7. Network Syslog ──
  const sysPerDevice = VOLUME.syslog.perDevice[i.syslogLevel] || VOLUME.syslog.perDevice.warnings;
  const sysPerFw     = VOLUME.syslog.perFirewall[i.syslogLevel] || VOLUME.syslog.perFirewall.warnings;
  const nonFwDevices = Math.max(0, i.devices - i.firewalls);
  const sysLow  = nonFwDevices * sysPerDevice.low + i.firewalls * sysPerFw.low;
  const sysHigh = nonFwDevices * sysPerDevice.high + i.firewalls * sysPerFw.high;
  subsystems.push({
    name: 'Network Syslog',
    icon: '🖧',
    type: 'log',
    low:  sysLow,
    high: sysHigh,
    avgSize: VOLUME.syslog.avgSizeBytes,
    unit: 'events',
    methodology: `${fmt(nonFwDevices)} devices × ${fmt(sysPerDevice.low)}–${fmt(sysPerDevice.high)} + ${i.firewalls} firewalls × ${fmt(sysPerFw.low)}–${fmt(sysPerFw.high)} (${i.syslogLevel} level)`,
  });

  // ── 8. NetFlow Records ──
  if (i.netflowSampling > 0) {
    const samplingFactor = 1 / i.netflowSampling;  // 1:100 → 0.01
    const nfLow  = i.firewalls * VOLUME.netflow.perFirewallBase.low * samplingFactor;
    const nfHigh = i.firewalls * VOLUME.netflow.perFirewallBase.high * samplingFactor;
    subsystems.push({
      name: 'NetFlow Records',
      icon: '🌊',
      type: 'log',
      low:  Math.round(nfLow),
      high: Math.round(nfHigh),
      avgSize: VOLUME.netflow.avgSizeBytes,
      unit: 'records',
      methodology: `${i.firewalls} firewalls × ${fmt(VOLUME.netflow.perFirewallBase.low)}–${fmt(VOLUME.netflow.perFirewallBase.high)} base flows × 1:${i.netflowSampling} sampling`,
    });
  }

  // ── 9. Mirth Connect Metrics ──
  const mirthDDU = i.mirthChannels * VOLUME.mirth.metricsPerChannelPerDay;
  subsystems.push({
    name: 'Mirth Connect Metrics',
    icon: '⚡',
    type: 'metric',
    low:  mirthDDU,
    high: mirthDDU,
    avgSize: 0,
    unit: 'DDUs',
    methodology: `${i.mirthChannels} channels × 6 metrics × 1440 polls/day = ${fmt(mirthDDU)} DDUs`,
  });

  // ── 10. Network Device Metrics (SNMP) ──
  const pollsPerDay = Math.round(86400 / i.snmpInterval);
  const avgIfaces = VOLUME.snmp.avgInterfacesPerDevice;
  const ddusPerDevice = (VOLUME.snmp.metricsPerDevicePerPoll + avgIfaces * VOLUME.snmp.metricsPerInterfacePerPoll) * pollsPerDay;
  const snmpDDU = i.devices * ddusPerDevice;
  subsystems.push({
    name: 'Network Metrics (SNMP)',
    icon: '📊',
    type: 'metric',
    low:  snmpDDU,
    high: snmpDDU,
    avgSize: 0,
    unit: 'DDUs',
    methodology: `${i.devices} devices × (${VOLUME.snmp.metricsPerDevicePerPoll} + ${avgIfaces} ifaces × ${VOLUME.snmp.metricsPerInterfacePerPoll}) × ${fmt(pollsPerDay)} polls/day`,
  });

  // ── DPS Calculations ──
  for (const s of subsystems) {
    if (s.type === 'log') {
      s.gibLow  = (s.low * s.avgSize) / (1024 ** 3);
      s.gibHigh = (s.high * s.avgSize) / (1024 ** 3);
      s.dpsLow  = s.gibLow * DPS_RATES.logIngestPerGiB;
      s.dpsHigh = s.gibHigh * DPS_RATES.logIngestPerGiB;
      s.storageDpsLow  = s.gibLow * i.retentionDays * DPS_RATES.logStoragePerGiBDay;
      s.storageDpsHigh = s.gibHigh * i.retentionDays * DPS_RATES.logStoragePerGiBDay;
    } else {
      s.gibLow = 0;
      s.gibHigh = 0;
      s.dpsLow  = (s.low / 1000) * DPS_RATES.metricPer1000DDU;
      s.dpsHigh = (s.high / 1000) * DPS_RATES.metricPer1000DDU;
      s.storageDpsLow = 0;
      s.storageDpsHigh = 0;
    }
  }

  // ── Totals ──
  const totalDpsLow  = subsystems.reduce((a, s) => a + s.dpsLow + s.storageDpsLow, 0);
  const totalDpsHigh = subsystems.reduce((a, s) => a + s.dpsHigh + s.storageDpsHigh, 0);

  return { subsystems, inputs: i, totalDpsLow, totalDpsHigh };
}

function avg(range) {
  return (range.low + range.high) / 2;
}

// ── Render Results ───────────────────────────────────────────────

function renderResults(r) {
  const { subsystems, inputs, totalDpsLow, totalDpsHigh } = r;
  const totalDpsMid = (totalDpsLow + totalDpsHigh) / 2;

  // Hero stats
  document.getElementById('total-daily-dps').textContent = `${totalDpsLow.toFixed(1)} – ${totalDpsHigh.toFixed(1)}`;
  document.getElementById('total-monthly-dps').textContent = `${(totalDpsLow * 30).toFixed(0)} – ${(totalDpsHigh * 30).toFixed(0)}`;

  if (inputs.dpsRate > 0) {
    document.getElementById('cost-hero').style.display = '';
    document.getElementById('total-monthly-cost').textContent =
      `$${fmt(Math.round(totalDpsLow * 30 * inputs.dpsRate))} – $${fmt(Math.round(totalDpsHigh * 30 * inputs.dpsRate))}`;
  } else {
    document.getElementById('cost-hero').style.display = 'none';
  }

  // Volume breakdown table
  const tbody = document.getElementById('results-body');
  tbody.innerHTML = '';

  // Colors for chart bars
  const colors = ['#4f8cff','#34d399','#f87171','#fbbf24','#a78bfa','#fb923c','#38bdf8','#e879f9','#22d3ee','#84cc16'];

  // Find max for bar scaling
  const maxDps = Math.max(...subsystems.map(s => s.dpsHigh + s.storageDpsHigh));

  subsystems.forEach((s, idx) => {
    const color = colors[idx % colors.length];
    const totalDpsS = s.dpsHigh + s.storageDpsHigh;
    const barWidth = maxDps > 0 ? (totalDpsS / maxDps * 100) : 0;

    const volumeStr = s.type === 'log'
      ? `${fmtK(s.low)} – ${fmtK(s.high)} ${s.unit}`
      : `${fmtK(s.low)} ${s.unit}`;
    const gibStr = s.type === 'log'
      ? `${s.gibLow.toFixed(2)} – ${s.gibHigh.toFixed(2)} GiB`
      : `${fmtK(s.low)} DDUs`;

    tbody.innerHTML += `
      <tr>
        <td>
          <span class="subsys-dot" style="background:${color}"></span>
          ${s.icon} ${s.name}
          <div class="bar-container"><div class="bar-fill" style="width:${barWidth}%;background:${color}"></div></div>
        </td>
        <td>${volumeStr}</td>
        <td>${gibStr}</td>
        <td>${s.dpsLow.toFixed(2)}</td>
        <td>${(s.dpsHigh + s.storageDpsHigh).toFixed(2)}</td>
      </tr>`;
  });

  document.getElementById('total-low-dps').innerHTML = `<strong>${totalDpsLow.toFixed(2)}</strong>`;
  document.getElementById('total-high-dps').innerHTML = `<strong>${totalDpsHigh.toFixed(2)}</strong>`;

  // Storage table
  const sBody = document.getElementById('storage-body');
  sBody.innerHTML = '';
  let storTotalIngest = 0, storTotalVol = 0, storTotalDps = 0;
  const logSystems = subsystems.filter(s => s.type === 'log');
  logSystems.forEach(s => {
    const avgGib = (s.gibLow + s.gibHigh) / 2;
    const storedVol = avgGib * inputs.retentionDays;
    const storageDps = (s.storageDpsLow + s.storageDpsHigh) / 2;
    storTotalIngest += avgGib;
    storTotalVol += storedVol;
    storTotalDps += storageDps;
    sBody.innerHTML += `
      <tr>
        <td>${s.icon} ${s.name}</td>
        <td>${avgGib.toFixed(2)} GiB</td>
        <td>${inputs.retentionDays}</td>
        <td>${storedVol.toFixed(1)} GiB</td>
        <td>${storageDps.toFixed(3)}</td>
      </tr>`;
  });
  document.getElementById('storage-total-ingest').textContent = `${storTotalIngest.toFixed(2)} GiB`;
  document.getElementById('storage-total-vol').textContent = `${storTotalVol.toFixed(1)} GiB`;
  document.getElementById('storage-total-dps').innerHTML = `<strong>${storTotalDps.toFixed(3)}</strong>`;

  // Assumptions
  const assumptions = document.getElementById('assumptions-list');
  assumptions.innerHTML = `
    <ul class="assumptions-ul">
      <li><strong>SIEM Audit Level (${inputs.auditLevel}):</strong> Based on Epic-published audit event categories. "Medium" = Epic default ClinDoc + Orders + Meds + Login. "High" adds context changes, chart access logging, and Break-the-Glass detail.</li>
      <li><strong>HL7 Volume:</strong> Derived from max(interface-based, encounter-based) estimate. Real volume depends on message types routed per interface (ADT, ORM, ORU, MDM, SIU).</li>
      <li><strong>FHIR API:</strong> Includes both internal Interconnect calls (Epic → Epic) and external Care Everywhere/TEFCA queries. Patient-facing FHIR (MyChart API) counted separately.</li>
      <li><strong>NetFlow:</strong> Volume is extremely sensitive to sampling rate. A 1:1 collection on an 8-firewall campus can generate 40–160M records/day (~16–64 GiB). Use 1:100 or higher for cost control.</li>
      <li><strong>Mirth Metrics:</strong> 6 metrics per channel (received, sent, errors, filtered, queue depth, status) at 1-minute resolution. Channel count is the primary driver.</li>
      <li><strong>Network SNMP:</strong> Assumes ${VOLUME.snmp.avgInterfacesPerDevice} avg interfaces/device. Core switches with 48+ ports will produce proportionally more data.</li>
      <li><strong>DPS Rates:</strong> Illustrative rates (~1 DPS/GiB log ingest, ~0.001 DPS/1000 DDUs metrics). ${inputs.dpsRate > 0 ? 'Using your provided rate of $' + inputs.dpsRate + '/DPS/month.' : 'Provide your contract rate for dollar estimates.'}</li>
      <li><strong>Variance:</strong> ±30% range reflects differences in clinical workflows, seasonal volume, shift patterns, and infrastructure age across healthcare organizations.</li>
    </ul>`;

  // Input summary
  const summary = document.getElementById('input-summary');
  summary.innerHTML = `
    <div class="summary-item"><span class="s-label">Staffed Beds</span><span class="s-value">${fmt(inputs.beds)}</span></div>
    <div class="summary-item"><span class="s-label">Daily Encounters</span><span class="s-value">${fmt(inputs.encounters)}</span></div>
    <div class="summary-item"><span class="s-label">Peak Epic Users</span><span class="s-value">${fmt(inputs.peakUsers)}</span></div>
    <div class="summary-item"><span class="s-label">MyChart Patients/mo</span><span class="s-value">${fmt(inputs.myChartPatients)}</span></div>
    <div class="summary-item"><span class="s-label">Epic Modules</span><span class="s-value">${inputs.epicModules}</span></div>
    <div class="summary-item"><span class="s-label">SIEM Audit Level</span><span class="s-value">${inputs.auditLevel}</span></div>
    <div class="summary-item"><span class="s-label">Network Devices</span><span class="s-value">${fmt(inputs.devices)}</span></div>
    <div class="summary-item"><span class="s-label">Firewalls</span><span class="s-value">${inputs.firewalls}</span></div>
    <div class="summary-item"><span class="s-label">Mirth Channels</span><span class="s-value">${inputs.mirthChannels}</span></div>
    <div class="summary-item"><span class="s-label">HL7 Interfaces</span><span class="s-value">${inputs.hl7Interfaces}</span></div>
    <div class="summary-item"><span class="s-label">Sites</span><span class="s-value">${inputs.sites}</span></div>
    <div class="summary-item"><span class="s-label">CE Partners</span><span class="s-value">${inputs.cePartners}</span></div>
    <div class="summary-item"><span class="s-label">Syslog Level</span><span class="s-value">${inputs.syslogLevel}</span></div>
    <div class="summary-item"><span class="s-label">NetFlow Sampling</span><span class="s-value">1:${inputs.netflowSampling || 'off'}</span></div>
    <div class="summary-item"><span class="s-label">SNMP Interval</span><span class="s-value">${inputs.snmpInterval}s</span></div>
    <div class="summary-item"><span class="s-label">Retention</span><span class="s-value">${inputs.retentionDays} days</span></div>
  `;
}

// ── CSV Export ────────────────────────────────────────────────────

function exportCSV() {
  const r = calculate();
  let csv = 'Subsystem,Type,Volume Low,Volume High,Unit,GiB Low,GiB High,DPS/Day Low,DPS/Day High,Methodology\n';
  for (const s of r.subsystems) {
    csv += `"${s.name}","${s.type}",${s.low},${s.high},"${s.unit}",${s.gibLow.toFixed(3)},${s.gibHigh.toFixed(3)},${s.dpsLow.toFixed(4)},${(s.dpsHigh + s.storageDpsHigh).toFixed(4)},"${s.methodology}"\n`;
  }
  csv += `\n"TOTAL","",,,,"","",${r.totalDpsLow.toFixed(4)},${r.totalDpsHigh.toFixed(4)},""\n`;
  csv += `\nInputs\n`;
  for (const [k, v] of Object.entries(r.inputs)) {
    csv += `"${k}","${v}"\n`;
  }

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `dps-estimate-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Helpers ──────────────────────────────────────────────────────

function fmtK(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toLocaleString('en-US');
}
