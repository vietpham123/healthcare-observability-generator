/* Healthcare Observability Generator — Frontend Logic */

const API = "";
let pollInterval = null;

// ── Logging ──────────────────────────────────────────────────────

function log(msg, level = "info") {
  const el = document.getElementById("activity-log");
  const ts = new Date().toLocaleTimeString();
  const entry = document.createElement("p");
  entry.className = `log-entry ${level}`;
  entry.textContent = `[${ts}] ${msg}`;
  el.prepend(entry);
  // Keep last 100 entries
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

// ── Generator controls ───────────────────────────────────────────

async function controlGenerator(name, action) {
  log(`${action === "start" ? "Starting" : "Stopping"} ${name} generator…`);
  try {
    const result = await api("POST", `/api/generators/${name}/${action}`);
    log(`${name}: ${result.running ? "running" : "stopped"}`, result.running ? "success" : "warn");
    refreshStatus();
  } catch (e) { /* logged in api() */ }
}

async function startAll() {
  log("Starting all generators…");
  await api("POST", "/api/generators/start-all");
  log("All generators started", "success");
  refreshStatus();
}

async function stopAll() {
  log("Stopping all generators…");
  await api("POST", "/api/generators/stop-all");
  log("All generators stopped", "warn");
  refreshStatus();
}

// ── Scenario controls ────────────────────────────────────────────

async function toggleScenario(key, checked) {
  const action = checked ? "activate" : "deactivate";
  log(`${action}: ${key}`);
  try {
    await api("POST", `/api/scenarios/${key}/${action}`);
    log(`Scenario ${key} ${action}d`, checked ? "success" : "warn");
    refreshStatus();
  } catch (e) {
    // Revert toggle on error
    const cb = document.getElementById(`toggle-${key}`);
    if (cb) cb.checked = !checked;
  }
}

async function deactivateAll() {
  await api("POST", "/api/scenarios/deactivate-all");
  log("All scenarios deactivated", "warn");
  refreshStatus();
}

async function reloadScenarios() {
  const result = await api("POST", "/api/scenarios/reload");
  log(`Scenarios reloaded (${result.count} available)`, "info");
  refreshStatus();
}

// ── Status updates ───────────────────────────────────────────────

function updateGeneratorBadge(name, running) {
  const badge = document.getElementById(`${name}-status`);
  if (!badge) return;
  badge.textContent = running ? "Running" : "Stopped";
  badge.className = `status-badge ${running ? "running" : ""}`;
}

function renderScenarios(scenarios) {
  const grid = document.getElementById("scenarios-grid");
  if (!scenarios || !scenarios.length) {
    grid.innerHTML = '<p class="loading">No scenarios found.</p>';
    return;
  }

  grid.innerHTML = scenarios.map(s => `
    <div class="scenario-row ${s.active ? "active" : ""}" id="row-${s.key}">
      <label class="scenario-toggle">
        <input type="checkbox" id="toggle-${s.key}" ${s.active ? "checked" : ""}
               onchange="toggleScenario('${s.key}', this.checked)">
        <span class="toggle-slider"></span>
      </label>
      <div class="scenario-info">
        <div class="scenario-name">${escHtml(s.name)}</div>
        <div class="scenario-desc" title="${escHtml(s.description)}">${escHtml(s.description)}</div>
      </div>
      <div class="scenario-badges">
        <span class="badge badge-epic">Epic</span>
        ${s.has_network_correlation ? '<span class="badge badge-network">Network</span>' : ""}
      </div>
    </div>
  `).join("");
}

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

async function refreshStatus() {
  try {
    const data = await api("GET", "/api/status");
    updateGeneratorBadge("epic", data.generators.epic.running);
    updateGeneratorBadge("network", data.generators.network.running);
    renderScenarios(data.scenarios);
  } catch (e) { /* logged */ }
}

// ── Init ─────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  refreshStatus();
  pollInterval = setInterval(refreshStatus, 5000);
  log("Control panel ready", "success");
});
