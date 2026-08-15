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
    <input id="savePath" placeholder="Paste a full .sav path here, example: D:\\alroc\\codepup\\rolo3\\POKEMON W.sav">
    <div class="button-row">
      <button type="button" onclick="fillSavePath('D:\\alroc\\codepup\\rolo3\\POKEMON W.sav', 'white')">
        Use White sample path
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
    <p class="muted">Requires BizHawk Lua bridge listening on localhost. Safe buttons only for now.</p>
    <div class="button-row">
      <button type="button" onclick="emulatorState()">Get State</button>
      <button type="button" onclick="pressButton('A')">A</button>
      <button type="button" onclick="pressButton('B')">B</button>
      <button type="button" onclick="pressButton('Start')">Start</button>
      <button type="button" onclick="pressButton('Select')">Select</button>
      <button type="button" onclick="pressButton('Up')">Up</button>
      <button type="button" onclick="pressButton('Down')">Down</button>
      <button type="button" onclick="pressButton('Left')">Left</button>
      <button type="button" onclick="pressButton('Right')">Right</button>
      <button type="button" onclick="frameAdvance(30)">Advance 30f</button>
      <button type="button" onclick="pressSequence(['A','A','A'])">AAA</button>
      <button type="button" onclick="emulatorPost('/api/emulator/pause', {})">Pause</button>
      <button type="button" onclick="emulatorPost('/api/emulator/resume', {})">Resume</button>
      <button type="button" onclick="checkpointSave()">Save CP</button>
      <button type="button" onclick="checkpointLoad()">Load CP</button>
      <button type="button" onclick="emulatorScreenshot()">Screenshot</button>
    </div>
    <pre id="emulatorOutput">Not connected.</pre>
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
async function runReport() {
  const error = document.getElementById('error');
  error.textContent = '';
  const savePath = document.getElementById('savePath').value.trim();
  if (!savePath) {
    error.textContent = 'Paste or quick-fill a real .sav path first. Placeholder text is not a value.';
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
    renderReport(data);
  } catch (err) {
    error.textContent = err.message || String(err);
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
}

async function emulatorState() {
  await apiToPre('/api/emulator/state', { method: 'GET' }, 'emulatorOutput');
}

async function emulatorPost(url, body) {
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

async function emulatorScreenshot() {
  await apiToPre('/api/emulator/screenshot', { method: 'GET' }, 'emulatorOutput');
}

async function telemetryFetch() {
  await apiToPre('/api/telemetry', { method: 'GET' }, 'telemetryOutput');
}

function connectTelemetry() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socket = new WebSocket(`${protocol}//${location.host}/ws/telemetry`);
  socket.onmessage = (event) => {
    document.getElementById('telemetryOutput').textContent = event.data;
  };
  socket.onerror = () => {
    document.getElementById('telemetryOutput').textContent = 'Telemetry WebSocket error.';
  };
}

async function voiceConfig() {
  const mode = document.getElementById('voiceMode').value;
  await apiToPre('/api/voice/config?mode=' + encodeURIComponent(mode), { method: 'GET' }, 'voiceOutput');
}

async function voiceRealtimeSession() {
  const mode = document.getElementById('voiceMode').value;
  await apiToPre('/api/voice/realtime-session?mode=' + encodeURIComponent(mode), {
    method: 'POST'
  }, 'voiceOutput');
}

async function validatorEvent() {
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

async function apiToPre(url, options, elementId) {
  const element = document.getElementById(elementId);
  try {
    const response = await fetch(url, options);
    const data = await readJsonOrText(response);
    element.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    element.textContent = err.message || String(err);
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

document.getElementById('run').addEventListener('click', runReport);
connectTelemetry();
</script>
</body>
</html>
"""
