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
    <input id="savePath" placeholder="D:\\alroc\\codepup\\rolo3\\POKEMON W.sav">

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

    <label><input id="includeParty" type="checkbox" checked> Count party as currently owned</label>

    <button id="run">Read Save</button>
    <p id="error" class="error"></p>
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
  const payload = {
    save_path: document.getElementById('savePath').value,
    game: document.getElementById('game').value,
    copy: 'auto',
    scope: document.getElementById('scope').value,
    include_party: document.getElementById('includeParty').checked
  };
  try {
    const response = await fetch('/api/pc-living-dex', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(JSON.stringify(data, null, 2));
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

document.getElementById('run').addEventListener('click', runReport);
</script>
</body>
</html>
"""
