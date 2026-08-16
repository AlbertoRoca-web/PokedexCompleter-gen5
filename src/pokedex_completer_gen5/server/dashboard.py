from __future__ import annotations

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PokedexCompleter Gen 5</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; background: #101820; color: #f7f7f7; }
    main { max-width: 1100px; margin: 0 auto; }
    .card { background: #1d2b36; border: 1px solid #344b5c; border-radius: 12px; padding: 1rem; margin: 1rem 0; }
    label { display: block; margin: .75rem 0 .25rem; font-weight: 650; }
    .button-row { display: flex; flex-wrap: wrap; gap: .5rem; }
    input, select, button { font: inherit; border-radius: 8px; border: 1px solid #5d7487; padding: .55rem; }
    input, select { width: min(100%, 760px); background: #0f1720; color: #f7f7f7; }
    button { background: #68d391; color: #102018; font-weight: 700; cursor: pointer; margin-top: 1rem; }
    button:hover { background: #9ae6b4; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: .75rem; }
    .stat { background: #0f1720; padding: .75rem; border-radius: 10px; border: 1px solid #344b5c; }
    .stat strong { display: block; font-size: 1.6rem; }
    pre { overflow: auto; background: #0a1016; padding: 1rem; border-radius: 10px; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border-bottom: 1px solid #344b5c; padding: .5rem; text-align: left; }
    .muted { color: #b8c7d4; }
    .error { color: #feb2b2; white-space: pre-wrap; }
    .status-panel {
      background: #0f1720; border: 1px solid #344b5c; border-radius: 10px;
      padding: .75rem; margin: .75rem 0;
    }
    .status-ready { border-color: #68d391; }
    .status-warn { border-color: #f6ad55; }
    .status-bad { border-color: #fc8181; }
  </style>
</head>
<body>
<main>
  <h1>Gen 5 PC Living Dex Dashboard</h1>
  <p class="muted">
    Local web UI for reading a save file, comparing PC/party physical bodies,
    and driving future emulator tools. No save upload required.
  </p>

  <section class="card">
    <h2>PC Living Dex Report</h2>
    <label for="savePath">Save path</label>
    <input id="savePath"
      placeholder="Paste a full .sav path here, example: D:\\Users\\alroc\\Downloads\\rolplete\\POKEMON W.sav">
    <div class="button-row">
      <button type="button" onclick="fillSavePath('D:\\Users\\alroc\\Downloads\\rolplete\\POKEMON W.sav', 'white')">
        Use completed White save path
      </button>
      <button type="button" onclick="fillSavePath('D:\\alroc\\codepup\\POKEMON B2.sav', 'black2')">
        Use Black 2 sample path
      </button>
    </div>

    <label for="game">Game</label>
    <select id="game">
      <option value="white">Pokemon White</option>
      <option value="black">Pokemon Black</option>
      <option value="white2">Pokemon White 2</option>
      <option value="black2">Pokemon Black 2</option>
    </select>

    <label for="scope">Scope</label>
    <select id="scope">
      <option value="regional">Regional Unova</option>
      <option value="national">National (pending)</option>
    </select>

    <label for="targetPolicy">Target policy</label>
    <select id="targetPolicy">
      <option value="game-regional">Game regional: version-aware Unova living dex</option>
      <option value="all-regional">All regional: every BW Unova dex entry</option>
      <option value="catchable-only">Catchable only: direct in-game targets</option>
    </select>

    <label><input id="includeParty" type="checkbox" checked> Count party as currently owned</label>

    <button id="run">Read Save</button>
    <p id="error" class="error"></p>
  </section>

  <section class="card">
    <h2>Emulator Control Skeleton</h2>
    <p class="muted">
      Launch starts BizHawk + White with the Lua bridge via --lua.
      If controls fail, check Lua Console.
    </p>
    <div class="button-row">
      <button type="button" onclick="launchBizHawk()">Launch BizHawk + White</button>
      <button type="button" onclick="diagnoseBridge()">Diagnose Bridge</button>
      <button type="button" onclick="ensureReady()">Ensure Ready</button>
      <button type="button" onclick="emulatorState()">Get State</button>
      <button type="button" onclick="pressButton('confirm')">Confirm (A / keyboard X)</button>
      <button type="button" onclick="pressButton('cancel')">Cancel (B / keyboard Z)</button>
      <button type="button" onclick="pressButton('menu')">Menu (X / keyboard S)</button>
      <button type="button" onclick="pressButton('registered-item')">Registered Item (Y / keyboard A)</button>
      <button type="button" onclick="pressButton('Start')">Start (Enter)</button>
      <button type="button" onclick="pressButton('Select')">Select (Space)</button>
      <button type="button" onclick="pressButton('Up')">Up</button>
      <button type="button" onclick="pressButton('Down')">Down</button>
      <button type="button" onclick="pressButton('Left')">Left</button>
      <button type="button" onclick="pressButton('Right')">Right</button>
      <button type="button" onclick="pressButton('L')">L (keyboard W)</button>
      <button type="button" onclick="pressButton('R')">R (keyboard E)</button>
      <button type="button" onclick="frameAdvance(30)">Advance 30f</button>
      <button type="button" onclick="pressSequence(['confirm','confirm','confirm'])">Confirm x3</button>
      <button type="button" onclick="emulatorPost('/api/emulator/pause', {})">Pause</button>
      <button type="button" onclick="emulatorPost('/api/emulator/resume', {})">Resume</button>
      <button type="button" onclick="checkpointSave()">Save CP</button>
      <button type="button" onclick="checkpointLoad()">Load CP</button>
      <button type="button" onclick="emulatorScreenshot()">Screenshot</button>
      <button type="button" onclick="screenshotAnalysisFetch()">Screenshot Analysis</button>
      <button type="button" onclick="waitInformativeScreenshot()">Wait Informative Screenshot</button>
      <button type="button" onclick="artifactListFetch()">Artifacts</button>
      <button type="button" onclick="memoryDomainsFetch()">Memory Domains</button>
      <input id="memoryDomain" placeholder="domain e.g. Main RAM" style="max-width:150px;">
      <input id="memoryAddress" placeholder="address hex/dec" style="max-width:130px;">
      <input id="memoryLength" placeholder="len" value="32" style="max-width:60px;">
      <button type="button" onclick="memoryReadBytesFetch()">Read Bytes</button>
      <button type="button" onclick="romIdentityFetch()">ROM Identity</button>
      <button type="button" onclick="emulatorInfoFetch()">Emulator Info</button>
      <button type="button" onclick="forceEmulatorSpeed()">Force 400% Speed</button>
    </div>
    <h3>Macros</h3>
    <div class="button-row">
      <button type="button" onclick="runMacro('/api/emulator/macro/open-menu')">Open Menu Macro</button>
      <button type="button" onclick="runMacro('/api/emulator/macro/close-menu')">Close Menu Macro</button>
      <button type="button" onclick="runTitleResumeMacro()">
        Title → Continue Save
      </button>
      <button type="button" onclick="macroFeedback('success')">Macro Worked</button>
      <button type="button" onclick="macroFeedback('failure')">Macro Failed</button>
      <button type="button" onclick="macroFeedback('uncertain')">Macro Uncertain</button>
    </div>
    <div id="macroStatus" class="status-panel status-warn">
      No macro run yet. Run Open Menu Macro, then confirm whether it worked.
    </div>
    <div id="emulatorStatus" class="status-panel status-warn">
      Status: not checked yet. Click Launch or Diagnose.
    </div>
    <div class="status-panel">
      <strong>Latest screenshot</strong><br>
      <img id="latestScreenshot" alt="Latest emulator screenshot"
           style="max-width:100%; image-rendering: pixelated; display:none;
                  border:1px solid #334155; border-radius:8px; margin-top:8px;" />
    </div>
    <pre id="emulatorOutput">Not connected.</pre>
  </section>

  <section class="card">
    <h2>Visualizer / Runtime Spine</h2>
    <p class="muted">Structured state, durable trajectory logs, and cost-aware routing. Tiny dashboard, big bones.</p>
    <div class="button-row">
      <button type="button" onclick="semanticStateFetch()">Semantic State</button>
      <button type="button" onclick="trajectoryFetch()">Trajectory JSONL</button>
      <button type="button" onclick="modelRouterFetch()">Model Router</button>
      <button type="button" onclick="macroReliabilityFetch()">Macro Reliability</button>
    </div>
    <pre id="visualizerOutput">No visualizer data yet.</pre>
  </section>

  <section class="card">
    <h2>Telemetry</h2>
    <p class="muted">Live-ish local event stream. WebSocket reconnect is manual for now.</p>
    <button type="button" onclick="telemetryFetch()">Fetch Telemetry</button>
    <pre id="telemetryOutput">No telemetry yet.</pre>
  </section>

  <section class="card">
    <h2>Voice Copilot Skeleton</h2>
    <p class="muted">
      Future GPT Realtime voice mode. Talk-to-me mode narrates; rubberduck mode
      comments and sends observations to validation before actions.
    </p>
    <label for="voiceMode">Voice mode</label>
    <select id="voiceMode">
      <option value="off">Off</option>
      <option value="talk-to-me">Talk to me</option>
      <option value="rubberduck">Rubberduck validator commentary</option>
    </select>
    <button type="button" onclick="voiceConfig()">Check Voice Config</button>
    <button type="button" onclick="voiceRealtimeSession()">Create Realtime Session</button>
    <button type="button" onclick="validatorEvent()">Send Rubberduck Event</button>
    <pre id="voiceOutput">Voice disabled.</pre>
  </section>

  <section id="results" class="card" hidden>
    <h2>Results</h2>
    <div class="stats">
      <div class="stat"><span>Targets</span><strong id="targetCount">-</strong></div>
      <div class="stat"><span>PC Owned</span><strong id="pcOwned">-</strong></div>
      <div class="stat"><span>Party Owned</span><strong id="partyOwned">-</strong></div>
      <div class="stat"><span>Missing</span><strong id="missingCount">-</strong></div>
    </div>
    <h3>Missing Targets</h3>
    <table>
      <thead><tr><th>Regional</th><th>National</th><th>Name</th><th>Method</th></tr></thead>
      <tbody id="missingRows"></tbody>
    </table>
    <h3>Raw JSON</h3>
    <pre id="rawJson"></pre>
  </section>
</main>
<script>
let latestMacroRunId = null;

async function runReport() {
  await logUiEvent('read_save_clicked', currentUiState());
  const error = document.getElementById('error');
  error.textContent = '';
  const savePath = document.getElementById('savePath').value.trim();
  if (!savePath) {
    error.textContent = 'Paste or quick-fill a real .sav path first. Placeholder text is not a value.';
    await logUiEvent('read_save_blocked_empty_path', currentUiState());
    return;
  }
  const payload = {
    save_path: savePath,
    game: document.getElementById('game').value,
    copy: 'auto',
    scope: document.getElementById('scope').value,
    include_party: document.getElementById('includeParty').checked,
    target_policy: document.getElementById('targetPolicy').value
  };
  try {
    const response = await fetch('/api/pc-living-dex', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await readJsonOrText(response);
    if (!response.ok) throw new Error(formatApiError(data));
    await logUiEvent('read_save_success', {
      target_count: data.target_count,
      missing_count: data.missing_count,
      policy: data.target_policy
    });
    renderReport(data);
  } catch (err) {
    error.textContent = err.message || String(err);
    await logUiEvent('read_save_error', { error: error.textContent, state: currentUiState() });
  }
}

function renderReport(data) {
  document.getElementById('results').hidden = false;
  document.getElementById('targetCount').textContent = data.target_count;
  document.getElementById('pcOwned').textContent = data.pc_owned_target_count;
  document.getElementById('partyOwned').textContent = data.party_owned_target_count;
  document.getElementById('missingCount').textContent = data.missing_count;
  document.getElementById('rawJson').textContent = JSON.stringify(data, null, 2);

  const rows = document.getElementById('missingRows');
  rows.innerHTML = '';
  for (const target of data.missing_targets.slice(0, 200)) {
    const row = document.createElement('tr');
    row.innerHTML = [
      `<td>${target.regional ?? ''}</td>`,
      `<td>${target.national}</td>`,
      `<td>${target.name}</td>`,
      `<td>${target.method}</td>`
    ].join('');
    rows.appendChild(row);
  }
}

function fillSavePath(path, game) {
  document.getElementById('savePath').value = path;
  document.getElementById('game').value = game;
  logUiEvent('quick_fill_save_path', { path, game });
}

async function launchBizHawk() {
  await logUiEvent('emulator_launch_clicked', {});
  await apiToPre('/api/emulator/launch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wait_for_bridge: true })
  }, 'emulatorOutput', renderEmulatorStatus);
}

async function diagnoseBridge() {
  await logUiEvent('emulator_diagnostics_clicked', {});
  await apiToPre('/api/emulator/diagnostics', { method: 'GET' }, 'emulatorOutput', renderEmulatorStatus);
}

async function emulatorState() {
  await logUiEvent('emulator_get_state_clicked', {});
  await apiToPre('/api/emulator/state', { method: 'GET' }, 'emulatorOutput', renderEmulatorStatus);
}

async function emulatorPost(url, body) {
  await logUiEvent('emulator_action_clicked', { url, body });
  await apiToPre(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }, 'emulatorOutput');
}

async function pressButton(button) {
  await emulatorPost('/api/emulator/press', { button, frames: 1 });
}

async function pressSequence(buttons) {
  await emulatorPost('/api/emulator/press-sequence', { buttons, frames: 1, gap_frames: 1 });
}

async function frameAdvance(frames) {
  await emulatorPost('/api/emulator/frame-advance', { frames });
}

async function checkpointSave() {
  await emulatorPost('/api/emulator/checkpoint/save', { name: 'manual' });
}

async function checkpointLoad() {
  await emulatorPost('/api/emulator/checkpoint/load', { name: 'manual' });
}

async function ensureReady() {
  await apiToPre('/api/emulator/ensure-ready', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ relaunch_if_needed: true })
  }, 'emulatorOutput');
}

async function runMacro(url) {
  await logUiEvent('emulator_macro_clicked', { url });
  await apiToPre(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wait_frames: 12, visual_max_attempts: 3, visual_advance_frames: 20 })
  }, 'emulatorOutput', renderMacroStatus);
}

async function runTitleResumeMacro() {
  const payload = {
    initial_wait_frames: 120,
    wait_after_start_frames: 30,
    wait_after_continue_frames: 120,
    visual_max_attempts: 4,
    visual_advance_frames: 30,
    press_frames: 5,
    change_max_attempts: 10,
    change_advance_frames: 120
  };
  await logUiEvent('emulator_macro_clicked', { url: '/api/emulator/macro/resume-save-from-title', payload });
  await apiToPre('/api/emulator/macro/resume-save-from-title', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }, 'emulatorOutput', renderMacroStatus);
}

function renderMacroStatus(data) {
  if (!data.macro_name || !data.id) return;
  latestMacroRunId = data.id;
  const status = document.getElementById('macroStatus');
  status.className = 'status-panel status-warn';
  const visualStatus = data.verification?.status || data.verification?.mode || 'unknown';
  status.innerHTML = `<strong>${data.macro_name}</strong><br>` +
    `Expected: ${data.expected_result}<br>` +
    `Visual: ${visualStatus}<br>` +
    `<span class="muted">Status: ${data.status}. Click Macro Worked/Failed/Uncertain.</span>`;
}

async function macroFeedback(outcome) {
  const status = document.getElementById('macroStatus');
  if (!latestMacroRunId) {
    status.className = 'status-panel status-bad';
    status.textContent = 'Run a macro first, then label it. Nice try, time traveler.';
    return;
  }
  await apiToPre('/api/emulator/macro/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ macro_run_id: latestMacroRunId, outcome, payload: currentUiState() })
  }, 'emulatorOutput');
  status.className = outcome === 'success' ? 'status-panel status-ready' : 'status-panel status-warn';
  status.innerHTML = `<strong>Feedback saved:</strong> ${outcome}<br>` +
    `<span class="muted">Macro run ${latestMacroRunId}</span>`;
}

async function emulatorScreenshot() {
  await apiToPre('/api/emulator/screenshot', { method: 'GET' }, 'emulatorOutput');
  const img = document.getElementById('latestScreenshot');
  img.src = '/api/emulator/screenshot/latest.png?cacheBust=' + Date.now();
  img.style.display = 'block';
}

async function screenshotAnalysisFetch() {
  await apiToPre('/api/emulator/screenshot/latest-analysis', { method: 'GET' }, 'emulatorOutput');
}

async function waitInformativeScreenshot() {
  await apiToPre('/api/emulator/screenshot/wait-informative', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: 'dashboard', max_attempts: 5, advance_frames: 30 })
  }, 'emulatorOutput');
  const img = document.getElementById('latestScreenshot');
  img.src = '/api/emulator/screenshot/latest.png?cacheBust=' + Date.now();
  img.style.display = 'block';
}

async function artifactListFetch() {
  await apiToPre('/api/emulator/artifacts', { method: 'GET' }, 'emulatorOutput');
}

async function memoryDomainsFetch() {
  await apiToPre('/api/emulator/memory/domains', { method: 'GET' }, 'emulatorOutput');
}

function parseMemoryAddress(value) {
  const trimmed = value.trim();
  if (!trimmed) return 0;
  return Number.parseInt(trimmed, trimmed.toLowerCase().startsWith('0x') ? 16 : 10);
}

async function memoryReadBytesFetch() {
  const domain = document.getElementById('memoryDomain').value;
  const address = parseMemoryAddress(document.getElementById('memoryAddress').value);
  const length = Number.parseInt(document.getElementById('memoryLength').value || '32', 10);
  await apiToPre('/api/emulator/memory/read-bytes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, address, length })
  }, 'emulatorOutput');
}

async function romIdentityFetch() {
  await apiToPre('/api/emulator/rom', { method: 'GET' }, 'emulatorOutput');
}

async function emulatorInfoFetch() {
  await apiToPre('/api/emulator/info', { method: 'GET' }, 'emulatorOutput');
}

async function forceEmulatorSpeed() {
  await apiToPre('/api/emulator/speed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ percent: 400 })
  }, 'emulatorOutput');
}

async function telemetryFetch() {
  await apiToPre('/api/telemetry', { method: 'GET' }, 'telemetryOutput');
}

async function semanticStateFetch() {
  await apiToPre('/api/emulator/semantic-state', { method: 'GET' }, 'visualizerOutput');
}

async function trajectoryFetch() {
  await apiToPre('/api/trajectory', { method: 'GET' }, 'visualizerOutput');
}

async function modelRouterFetch() {
  await apiToPre('/api/ai/model-router', { method: 'GET' }, 'visualizerOutput');
}

async function macroReliabilityFetch() {
  await apiToPre('/api/emulator/macro/feedback', { method: 'GET' }, 'visualizerOutput');
}

let telemetrySocket = null;

function connectTelemetry() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  if (telemetrySocket && telemetrySocket.readyState === WebSocket.OPEN) return;
  telemetrySocket = new WebSocket(`${protocol}//${location.host}/ws/telemetry`);
  telemetrySocket.onmessage = (event) => {
    document.getElementById('telemetryOutput').textContent = event.data;
  };
  telemetrySocket.onerror = () => {
    document.getElementById('telemetryOutput').textContent = 'Telemetry WebSocket error.';
  };
}

function closeTelemetry() {
  if (telemetrySocket && telemetrySocket.readyState === WebSocket.OPEN) {
    telemetrySocket.close(1000, 'dashboard closing');
  }
}

window.addEventListener('pagehide', closeTelemetry);
window.addEventListener('beforeunload', closeTelemetry);

async function voiceConfig() {
  const mode = document.getElementById('voiceMode').value;
  await logUiEvent('voice_config_clicked', { mode });
  await apiToPre('/api/voice/config?mode=' + encodeURIComponent(mode), { method: 'GET' }, 'voiceOutput');
}

async function voiceRealtimeSession() {
  const mode = document.getElementById('voiceMode').value;
  await logUiEvent('voice_realtime_session_clicked', { mode });
  await apiToPre('/api/voice/realtime-session?mode=' + encodeURIComponent(mode), {
    method: 'POST'
  }, 'voiceOutput');
}

async function validatorEvent() {
  await logUiEvent('validator_event_clicked', {});
  await apiToPre('/api/validator/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_type: 'voice_commentary',
      message: 'Rubberduck event test from dashboard.',
      payload: { source: 'dashboard' }
    })
  }, 'voiceOutput');
}

function renderEmulatorStatus(data) {
  const status = document.getElementById('emulatorStatus');
  const diagnostics = data.diagnostics ?? data;
  const diagnosis = diagnostics.diagnosis;
  const bridgeAfterLaunch = data.native_bridge_after_launch ?? data.bridge_after_launch;
  const nativeBridge = diagnostics.native_bridge ?? data.native_bridge;
  if (!diagnosis && !bridgeAfterLaunch && !nativeBridge && !data.detail) return;

  let html = '';
  let css = 'status-panel status-warn';
  if (diagnosis) {
    css = diagnosis.status === 'ready' ? 'status-panel status-ready' : 'status-panel status-bad';
    html += `<strong>${diagnosis.status}</strong><br>${diagnosis.message}<br>`;
    html += `<span class="muted">Next: ${diagnosis.next_step}</span>`;
  }
  if (!diagnosis && data.detail) {
    css = 'status-panel status-bad';
    const detail = typeof data.detail === 'string' ? { error: data.detail } : data.detail;
    html += `<strong>bridge-error</strong><br>${detail.error ?? JSON.stringify(detail)}<br>`;
    if (detail.hint) html += `<span class="muted">Next: ${detail.hint}</span>`;
  }
  if (bridgeAfterLaunch) {
    html += `<br><span class="muted">Native bridge wait: ${bridgeAfterLaunch.ok ? 'connected' : 'not connected'} `;
    html += `after ${bridgeAfterLaunch.attempts} attempt(s).</span>`;
  }
  if (nativeBridge) {
    html += `<br><span class="muted">Native bridge server: `;
    html += `${nativeBridge.running ? 'running' : 'stopped'}, `;
    html += `${nativeBridge.connected ? 'connected' : 'not connected'} on port ${nativeBridge.port}</span>`;
  }
  status.className = css;
  status.innerHTML = html;
}

async function apiToPre(url, options, elementId, renderer) {
  const element = document.getElementById(elementId);
  try {
    const response = await fetch(url, options);
    const data = await readJsonOrText(response);
    element.textContent = JSON.stringify(data, null, 2);
    if (renderer) renderer(data);
    await logUiEvent('api_response', { url, ok: response.ok, status: response.status, data });
  } catch (err) {
    element.textContent = err.message || String(err);
    await logUiEvent('api_error', { url, error: element.textContent });
  }
}

async function readJsonOrText(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function formatApiError(data) {
  if (data && typeof data.detail === 'string') return data.detail;
  return JSON.stringify(data, null, 2);
}

function currentUiState() {
  return {
    save_path_present: Boolean(document.getElementById('savePath').value.trim()),
    game: document.getElementById('game').value,
    scope: document.getElementById('scope').value,
    target_policy: document.getElementById('targetPolicy').value,
    include_party: document.getElementById('includeParty').checked,
    voice_mode: document.getElementById('voiceMode').value
  };
}

async function logUiEvent(eventType, payload) {
  try {
    await fetch('/api/ui/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: eventType, payload })
    });
  } catch {
    // UI telemetry must never break the dashboard.
  }
}

document.getElementById('run').addEventListener('click', runReport);
logUiEvent('dashboard_loaded', currentUiState());
connectTelemetry();
</script>
</body>
</html>
"""
