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
  "normal-day-shift":        { icon: "🏥", prep: 5,  runtime: "Continuous",   tip: "Baseline — activate 5 min before demo for smooth charts." },
  "ransomware-attack":       { icon: "🦠", prep: 10, runtime: "60 min cycle", tip: "Login failures spike → Auth & Security pages turn RED. 4 phases: Recon → Harvest → Lateral → Exfil." },
  "insider-threat-snooping": { icon: "🕵️", prep: 10, runtime: "50 min cycle", tip: "BTG events spike → Security page turns RED. Employee browsing records after hours." },
  "hl7-interface-failure":   { icon: "🔌", prep: 10, runtime: "Escalating",   tip: "Mirth queue backs up → Integration page turns RED. FHIR errors + ETL failures." },
  "core-switch-failure":     { icon: "🔥", prep: 5,  runtime: "Continuous",   tip: "Devices go offline, CPU spikes → Network page turns RED." },
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
