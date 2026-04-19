/* Healthcare Observability Generator — Frontend Logic */

const API = "";
let pollInterval = null;
let pendingAction = false;  // Prevent double-clicks during deploy

// ── Logging ──────────────────────────────────────────────────────

function log(msg, level = "info") {
  const el = document.getElementById("activity-log");
  const ts = new Date().toLocaleTimeString();
  const entry = document.createElement("p");
  entry.className = `log-entry ${level}`;
  entry.textContent = `[${ts}] ${msg}`;
  el.prepend(entry);
  while (el.children.length > 100) el.removeChild(el.lastChild);
}

// ── API helpers ──────────────────────────────────────────────────

async function api(method, path, body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(`${API}${path}`, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return await res.json();
  } catch (e) {
    log(`API error: ${e.message}`, "error");
    throw e;
  }
}

// ── Scenario controls ────────────────────────────────────────────

async function selectScenario(key) {
  if (pendingAction) return;

  const row = document.getElementById(`row-${key}`);
  const isCurrentlyActive = row && row.classList.contains("active");

  if (isCurrentlyActive) {
    // Clicking the active scenario deactivates it → normal_shift
    pendingAction = true;
    setAllDisabled(true);
    log(`Deactivating ${key} → normal_shift...`);
    try {
      const result = await api("POST", `/api/scenarios/${key}/deactivate`);
      log(`Deactivated. Generator restarting with normal_shift.`, "warn");
      if (result.generator_restarted) {
        log("Generator restart triggered — takes ~30s to come online.", "info");
      }
    } catch (e) { /* logged */ }
    pendingAction = false;
    setAllDisabled(false);
    refreshStatus();
  } else {
    // Clicking a new scenario activates it (auto-deactivates previous)
    pendingAction = true;
    setAllDisabled(true);
    log(`Activating ${key}...`);
    try {
      const result = await api("POST", `/api/scenarios/${key}/activate`);
      const prev = result.previously_active || [];
      if (prev.length > 0) {
        log(`Switched from ${prev.join(", ")} → ${key}`, "success");
      } else {
        log(`Activated ${key} (epic: ${result.epic_scenario})`, "success");
      }
      if (result.generator_restarted) {
        log("Generator restart triggered — takes ~30s to come online.", "info");
      }
    } catch (e) { /* logged */ }
    pendingAction = false;
    setAllDisabled(false);
    refreshStatus();
  }
}

function setAllDisabled(disabled) {
  document.querySelectorAll(".scenario-row").forEach(row => {
    row.style.pointerEvents = disabled ? "none" : "";
    row.style.opacity = disabled ? "0.6" : "";
  });
}

async function deactivateAll() {
  if (pendingAction) return;
  pendingAction = true;
  setAllDisabled(true);
  try {
    await api("POST", "/api/scenarios/deactivate-all");
    log("All scenarios deactivated → normal_shift", "warn");
  } catch (e) { /* logged */ }
  pendingAction = false;
  setAllDisabled(false);
  refreshStatus();
}

async function reloadScenarios() {
  const result = await api("POST", "/api/scenarios/reload");
  log(`Scenarios reloaded (${result.count} available)`, "info");
  refreshStatus();
}

// ── Scenario prep metadata (mirrors walkthrough.js) ─────────────

const SCENARIO_PREP = {
  "normal-day-shift": { icon: "🏥", prep: 5, runtime: "Continuous", tip: "Baseline — activate 5 min before demo for smooth charts." },
  "normal_shift":     { icon: "🏥", prep: 5, runtime: "Continuous", tip: "Baseline — activate 5 min before demo for smooth charts." },
  "ed-surge":         { icon: "🚨", prep: 10, runtime: "Continuous", tip: "Run Normal first for 15 min, then switch to ED Surge for dramatic spike." },
  "ed_surge":         { icon: "🚨", prep: 10, runtime: "Continuous", tip: "Run Normal first for 15 min, then switch to ED Surge for dramatic spike." },
  "ransomware-attack":{ icon: "💀", prep: 30, runtime: "60 min (4 phases)", tip: "Start 30 min early. Present at T-10 to watch Phases 3-4 unfold live." },
  "ransomware":       { icon: "💀", prep: 30, runtime: "60 min (4 phases)", tip: "Start 30 min early. Present at T-10 to watch Phases 3-4 unfold live." },
  "brute_force":      { icon: "🔐", prep: 10, runtime: "60 min", tip: "Fastest demo — KPI turns RED in under 5 min. Great for time-constrained demos." },
  "hipaa_audit":      { icon: "📋", prep: 10, runtime: "60 min", tip: "Focus on Security & Compliance page — single billing user across 6+ departments." },
  "insider-threat-snooping": { icon: "🕵️", prep: 15, runtime: "50 min", tip: "Low-and-slow attack. Present as a mystery: 'Everything looks normal, but...'" },
  "insider_threat":   { icon: "🕵️", prep: 15, runtime: "50 min", tip: "Low-and-slow attack. Present as a mystery: 'Everything looks normal, but...'" },
  "privacy_breach":   { icon: "🔓", prep: 15, runtime: "50 min", tip: "Break-the-glass abuse. Good follow-up to HIPAA Audit scenario." },
  "epic-outage-network-root-cause": { icon: "🔌", prep: 10, runtime: "Continuous", tip: "Best for showing cross-domain root cause analysis. Network → Epic cascade." },
  "hl7-interface-failure": { icon: "🔀", prep: 10, runtime: "Continuous", tip: "Present as help-desk ticket: 'Lab results aren't showing in Epic.'" },
  "iomt-device-compromise": { icon: "💉", prep: 10, runtime: "Continuous", tip: "IoMT-specific audience. Emphasize segmentation as primary defense." },
  "mychart-credential-stuffing": { icon: "🤖", prep: 10, runtime: "Continuous", tip: "Pair with Brute Force for a 'credential attacks' demo track." },
  "mychart_peak":     { icon: "📱", prep: 10, runtime: "Continuous", tip: "Healthy portal traffic. Good baseline before credential stuffing demo." },
};

// ── Status updates ───────────────────────────────────────────────

function renderScenarios(scenarios) {
  const grid = document.getElementById("scenarios-grid");
  if (!scenarios || !scenarios.length) {
    grid.innerHTML = '<p class="loading">No scenarios found.</p>';
    return;
  }

  grid.innerHTML = scenarios.map(s => {
    const meta = SCENARIO_PREP[s.key] || {};
    const prepMin = meta.prep || "?";
    const guideLink = `/walkthrough#${s.key}`;
    return `
    <div class="scenario-row ${s.active ? "active" : ""}"
         id="row-${s.key}">
      <div class="scenario-radio" onclick="selectScenario('${s.key}')" role="button" tabindex="0"
           title="${s.active ? 'Click to deactivate' : 'Click to activate'}">
        <span class="radio-dot ${s.active ? "checked" : ""}"></span>
      </div>
      <div class="scenario-info" onclick="selectScenario('${s.key}')" role="button">
        <div class="scenario-name">${meta.icon || "📋"} ${escHtml(s.name)}</div>
        <div class="scenario-desc">${escHtml(s.description)}</div>
        <div class="scenario-meta">
          <span class="meta-prep" title="Activate this many minutes before your demo">⏱️ Prep: ${prepMin} min</span>
          <span class="meta-runtime" title="How long the scenario runs">${escHtml(meta.runtime || "")}</span>
          <a href="${guideLink}" class="meta-guide" onclick="event.stopPropagation()" title="View full demo walkthrough guide">📖 Demo Guide</a>
        </div>
        ${meta.tip ? `<div class="scenario-tip">💡 ${escHtml(meta.tip)}</div>` : ""}
      </div>
      <div class="scenario-badges">
        <span class="badge badge-epic">Epic</span>
        ${s.has_network_correlation ? '<span class="badge badge-network">Network</span>' : ""}
      </div>
    </div>`;
  }).join("");
}

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

async function refreshStatus() {
  if (pendingAction) return;  // Don't poll during action
  try {
    const data = await api("GET", "/api/status");
    renderScenarios(data.scenarios);
    // Update K8s status indicator if present
    const k8sEl = document.getElementById("k8s-status");
    if (k8sEl) {
      k8sEl.textContent = data.k8s_connected ? "Connected" : "Disconnected";
      k8sEl.className = data.k8s_connected ? "status-ok" : "status-err";
    }
  } catch (e) { /* logged */ }
}

// ── Init ─────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  refreshStatus();
  pollInterval = setInterval(refreshStatus, 5000);
  log("Control panel ready — select one scenario at a time", "success");
});
