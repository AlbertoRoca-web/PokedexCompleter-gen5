# Repository Capabilities, Live Progress, and Maximum-Use Plan

Last updated: 2026-08-22

## Executive Summary

PokedexCompleter Gen 5 is already much more than a save-file report script. It is a layered local automation system containing:

- a Generation 5 save reader;
- physical PC and party inventory extraction;
- regional Living Dex and catchable-target planning;
- evolution, breeding, nickname, legality, encounter, route-target, and travel-mode policies;
- a BizHawk + melonDS bridge with input, screenshots, frame advance, checkpoints, memory reads, and diagnostics;
- a generalized gameplay loop with battle-safe execution lanes and durable trajectory events;
- REST, WebSocket, MCP, CLI, browser dashboard, and Windows companion entry points;
- optional OpenAI, Anthropic, Google Gemini, Supabase, Hugging Face, voice, vision, RL, and desktop packaging dependencies;
- CI, secret checks, PyPI publishing, and now a wallet-safe multi-model orchestrator workflow.

The project is therefore **not missing a platform**. Its largest blocker remains reliable semantic game state and deterministic execution coverage. The correct next move is to strengthen those layers rather than replacing them with browser-controlled consumer chat tabs or asking an LLM to press every button.

## Live Game Progress

### Verified session state

During the current live Pokémon White session, the system and operator jointly achieved:

1. Loaded the known completed save safely.
2. Navigated from Nuvema Town onto Route 1.
3. Caught a wild Patrat for the physical Living Dex.
4. Caught a wild Lillipup while preserving an evolution reserve.
5. Updated route-target logic so Watchog is not redundantly targeted when the Patrat reserve can evolve into it.
6. Registered the Super Rod in the quick-select menu.
7. Navigated across the west-facing Route 1 stair/bridge approach to the real water landing.
8. Fished a female level 36 Basculin.
9. Caught that Basculin after safe ball retries.

### Important operational lessons

- Route 1's stair traversal is primarily west/left across the visible red-railed path. Repeated north/south guesses caused loops.
- The decorative/cliff-banked pond edges are not valid fishing banks.
- The usable water landing is reached by moving left across the stair passage.
- Registered-item selection still requires selecting Super Rod from the quick menu.
- Fishing has a roughly 10–15 second interaction window under the current lag/speed conditions.
- Battle Bag navigation is multi-stage: Bag -> Poké Balls -> ball -> Use.
- Repeat Ball is available and receives a strong bonus for previously registered species; Net Ball is also appropriate for Water types.
- Four-frame menu taps are more reliable than long held pulses in several menu contexts.
- Ten-frame overworld movement pulses can be eaten under lag; screenshots remain necessary while RAM semantics are incomplete.

### Progress source of truth

Runtime progress is recorded in local ignored artifacts under `.runtime/`, while durable policy state belongs in repository code and committed progress data. The save/PC/party reader remains the final physical-ownership authority.

## Architecture in One Diagram

```text
Browser Dashboard / CLI / External Agent
                 |
       REST + WebSocket + MCP
                 |
   Multi-Model Advisory Orchestrator
                 |
       Planner + Validator Policies
                 |
 Living Dex / Route / Encounter Engines
                 |
 Generalized Gameplay + Deterministic Macros
                 |
      Semantic State + Vision Fallback
                 |
        BizHawk Native Lua Bridge
                 |
         BizHawk + melonDS + SaveRAM
```

The invariant is:

```text
models advise -> validators gate -> deterministic executors act -> observations verify
```

## Repository Inventory

### `src/pokedex_completer_gen5/agents`

Contains planner boundaries, provider adapters, validator state, and voice configuration.

Implemented providers:

- OpenAI text planner;
- OpenAI image/vision planner;
- Anthropic text planner;
- Google Gemini text planner;
- provider factory;
- OpenAI-compatible local/alternative endpoint through the orchestrator.

The planner asks for strict structured Living Dex tasks. It does not directly mutate the game.

### `src/pokedex_completer_gen5/ai`

Contains:

- cost-aware task-to-model routing;
- dry-run benchmark case routing;
- multi-provider orchestration;
- single, routed, ensemble, and review modes;
- deterministic candidate synthesis;
- provider failure isolation;
- local OpenAI-compatible endpoint support.

### `src/pokedex_completer_gen5/autonomy`

Contains:

- durable autonomy budgets;
- dry-run and execute controls;
- generalized gameplay agent loop;
- HTTP gameplay environment;
- capture protocol rules;
- checkpoints and stuck detection.

This is a real supervisor spine, but it is not yet a fully independent regional-dex finisher because semantic state and deterministic navigation/capture coverage are incomplete.

### `src/pokedex_completer_gen5/dex`

Contains the Pokémon-domain brain:

- Black/White Unova species and acquisition data;
- guarded B2W2 support status;
- national and Gen 1–4 species metadata;
- direct and obtainable target reports;
- catch legality;
- route encounter policy;
- evolution knowledge;
- breeding knowledge and protocols;
- PC Living Dex inventory logic;
- route target selection;
- walking versus Fly transition planning;
- nickname generation;
- location knowledge.

Recent improvements include evolution-reserve awareness and map-aware route transition planning.

### `src/pokedex_completer_gen5/emulator`

Contains:

- BizHawk launch and readiness checks;
- native and legacy bridge clients;
- controller normalization;
- screenshots and checkpoints;
- frame advance and speed control;
- macro execution and feedback;
- title-screen safe resume;
- C-Gear handling;
- visual wait and screenshot classification;
- semantic-state profile scaffolding;
- memory diagnostics and ROM identification.

The native bridge is proven alive in the current session and exposes frame count, melonDS core information, screenshots, and input.

### `src/pokedex_completer_gen5/saveio`

Contains read-only Generation 5 parsing:

- active save-copy selection;
- PK5 decoding;
- party decoding;
- PC decoding;
- save report generation;
- cartridge/export safety paths;
- physical inventory reports.

This is the authoritative Living Dex ownership layer. Pokédex caught flags are deliberately not trusted.

### `src/pokedex_completer_gen5/server`

Contains:

- FastAPI REST service;
- local browser dashboard;
- WebSocket telemetry;
- MCP tool server and stdio entry point;
- local connection discovery;
- screenshot/artifact serving;
- emulator operations;
- AI router and orchestrator endpoints;
- voice skeleton endpoints.

The dashboard is a single embedded HTML module. It is functional, but future UI growth should split it into static assets or components before it becomes a 600-line swamp monster.

### `src/pokedex_completer_gen5/persistence` and `backend`

Contains:

- SQLite persistence;
- SQLAlchemy models and stores;
- artifacts and macro feedback;
- Living Dex progress state;
- optional Supabase report synchronization;
- sanitized cloud metadata storage.

### `scripts`

Contains operational tooling for:

- generalized and continuous play;
- RAM discovery and validation;
- paired action diffs;
- title/menu state probing;
- static NDS probes;
- location/evolution knowledge builds;
- cartridge save export;
- backend restart discipline;
- browser QA helper;
- local companion executable entry point;
- PyInstaller build.

### `lua`

Contains the BizHawk Lua bridge that connects emulator state and controls to the Python service.

### `tests`

Covers save parsing, Living Dex reports, route planning, gameplay-agent behavior, REST operations, provider health, vision payloads, semantic state, bridge behavior, model routing, safety policies, and orchestration.

## Interactive Software

### Local browser dashboard

Run:

```powershell
uv run rld serve --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

The dashboard supports:

- PC Living Dex reports;
- save-path quick fill;
- emulator launch and diagnosis;
- safe title resume;
- menu macros;
- controls, screenshots, semantic state, trajectory, and telemetry;
- checkpoint operations;
- voice configuration skeleton;
- multi-model advisory orchestration.

### Windows companion executable

Build:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\build_local_companion.ps1

# If the local backend currently locks .venv/Scripts/rld.exe:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\build_local_companion.ps1 -NoSync
```

Output:

```text
dist/PokedexCompleterAgent.exe
```

Run normally to start the API and open the browser dashboard:

```powershell
.\dist\PokedexCompleterAgent.exe
```

Run a non-mutating local scan:

```powershell
.\dist\PokedexCompleterAgent.exe --scan-only
```

The executable is a local companion, not a bundled emulator or ROM. ROMs, saves, secrets, and runtime artifacts remain external and ignored.

## Multi-Model Orchestrator

### Why APIs, not consumer browser tabs

Automating ChatGPT, Claude, or Gemini consumer web UIs is brittle, hard to test, dependent on cookies and interactive logins, and may violate provider terms. This repository now uses the supported integration boundary:

- authenticated provider APIs;
- optional OpenAI-compatible local endpoints;
- explicit backend environment configuration;
- no secret values in browser JavaScript;
- no secret values in telemetry;
- no browser-stored API keys.

### Supported modes

#### `single`

Use one explicit provider/model. Good for reproducibility and controlled spending.

#### `route`

Choose one configured provider based on prompt characteristics. This avoids paying three providers for routine work.

#### `ensemble`

Call up to three configured providers concurrently, retain every candidate and failure, then use deterministic synthesis. This is appropriate for architecture audits, recovery plans, and high-value decisions—not ordinary button timing.

#### `review`

Generate candidates from multiple providers and choose a structured reviewer result. This creates diversity without granting models direct action authority.

### CLI

Free capability check:

```powershell
uv run rld orchestrator-info
```

Routed request:

```powershell
uv run rld orchestrate "Audit the next Living Dex milestone" --mode route
```

Explicit provider:

```powershell
uv run rld orchestrate "Review this route plan" --mode single --provider anthropic
```

Ensemble:

```powershell
uv run rld orchestrate "Find safety gaps in the capture protocol" --mode ensemble --max-providers 3
```

### REST

Free capability endpoint:

```text
GET /api/ai/orchestrator
```

Paid advisory endpoint:

```text
POST /api/ai/orchestrate
```

Example body:

```json
{
  "prompt": "Audit the next safe deterministic milestone.",
  "mode": "ensemble",
  "provider": null,
  "model": null,
  "max_providers": 3
}
```

### Alternative/local models

Configure an OpenAI-compatible endpoint:

```env
OPENAI_COMPATIBLE_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_COMPATIBLE_API_KEY=local
AI_MODEL_COMPATIBLE=local-model
```

Compatible systems commonly include Ollama adapters, LM Studio, vLLM, and other OpenAI-compatible servers. Exact model names depend on the server.

## Secrets and Provider Configuration

The GitHub repository contains these confirmed secret names:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `HF_TOKEN`
- `PYPI_API_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`

GitHub Actions can inject those secrets into jobs, but secret values cannot be read back through the GitHub UI/API. Local software still needs local `.env` values if it should call providers from this computer.

Never commit `.env`, API keys, service-role keys, cookies, or tokens.

## GitHub Actions Workflows

### `ci.yml`

Runs on pushes and pull requests to `main`:

- installs Python 3.12 and uv;
- installs development dependencies;
- runs Ruff;
- runs Pyright;
- runs pytest.

### `publish-pypi.yml`

Manual only:

- lint;
- test;
- build distributions;
- publish through `PYPI_API_TOKEN`.

This should remain manual until versioning and release discipline mature.

### `secrets-smoke.yml`

Manual, no provider calls:

- checks whether expected secret names contain values;
- prints only configured/missing status;
- never prints secret values.

### `build-windows-companion.yml`

Manual or version-tag triggered:

- builds on `windows-latest`;
- smoke-tests `--scan-only`;
- uploads `PokedexCompleterAgent.exe` as a workflow artifact;
- does not embed secrets, saves, or ROMs.

### `orchestrator-smoke.yml`

Manual and wallet-safe by default:

- installs AI and test dependencies;
- runs the free orchestrator capability check;
- runs orchestration and REST tests;
- performs one paid provider request only when `run_live=true` is explicitly selected.

## MCP and External Agents

Run:

```powershell
uv run rld-mcp
```

The MCP server exposes semantic tools to external agents. The intended model-facing surface is task-level and safety-gated. Raw memory and direct input operations belong in developer/debug flows.

Code Puppy or another MCP-capable agent can use the project without being embedded into the executable. This separation keeps the app provider-neutral and avoids coupling the repository to one IDE or agent vendor.

## Current Capability Matrix

| Capability | Status | Evidence / limitation |
| --- | --- | --- |
| Gen 5 PK5 decode | Built | Read-only parser and tests. |
| Party extraction | Built | Physical party bodies parsed. |
| PC extraction | Built | Physical PC bodies parsed. |
| Active save-copy selection | Built | Uses save structure rather than guessing. |
| Regional BW Living Dex | Built | Physical target and missing reports. |
| B2W2 planner | Guarded | Explicitly unavailable rather than silently wrong. |
| Catchable targets | Built | Direct and obtainable modes. |
| Evolution/breeding rules | Partial but useful | Reserve-aware targeting now exists. |
| Route target planning | Partial | Route 1 and transition policies exist; world graph incomplete. |
| Fly-aware travel choice | Built policy | Execution remains incomplete. |
| BizHawk launch/readiness | Built | Current live bridge proven. |
| Input/screenshots/checkpoints | Built | Used throughout live session. |
| Safe title resume | Built | Visual verification and C-Gear handling. |
| Semantic RAM state | Major gap | Only tentative menu state verified. |
| Map ID / X / Y / facing | Missing | Must not be guessed. |
| Battle/transition RAM state | Missing | Visual fallback currently required. |
| Generalized gameplay agent | Built scaffold | Works with observation/action boundaries. |
| Deterministic route navigation | Partial | Human/vision supervision still needed. |
| Fishing | Proven manually | 10–15 second timing window under lag. |
| Wild capture | Proven manually | Basculin caught; generic verification still incomplete. |
| PC box automation | Missing | Needs safe deposit/withdraw verification. |
| REST dashboard | Built | Interactive local app. |
| WebSocket telemetry | Built | Local event stream. |
| MCP server | Built | Stdio agent integration. |
| OpenAI provider | Built | Requires local key and AI extra. |
| Anthropic provider | Built | Requires local key and AI extra. |
| Gemini provider | Built | Requires local key and AI extra. |
| OpenAI-compatible provider | Built | Requires local endpoint config. |
| Multi-model orchestration | Built | Advisory-only, budget-conscious modes. |
| Windows companion executable | Build path built | PyInstaller one-file app. |
| Supabase | Optional/partial | Sanitized report storage, not game-state authority. |
| Voice copilot | Skeleton | Config and realtime-session boundary, not full voice loop. |
| RL/Gymnasium | Planned | Optional dependency only. |

## What “Using the Project to the Max” Actually Means

Maximum use does **not** mean calling every premium model on every frame. That would maximize invoices, latency, and chaos—not progress.

The efficient hierarchy is:

1. Read save/RAM deterministically.
2. Execute known macros deterministically.
3. Use local image classification for verification.
4. Use one cheap routed model for bounded ambiguity.
5. Use ensemble/review only for expensive mistakes, architecture decisions, or repeated recovery failure.
6. Persist every observation and validator result.
7. Promote successful supervised sequences into tested macros.

### Suggested provider roles

- **OpenAI:** short planning, structured responses, image analysis, recovery escalation.
- **Anthropic:** long architecture/policy review and contradiction hunting.
- **Gemini:** alternate reasoning and image-heavy review.
- **OpenAI-compatible local model:** cheap classification, summarization, and experimentation when quality is sufficient.

These are defaults, not dogma. Measure latency, cost, schema compliance, and correctness on repository benchmark cases.

## Safety Boundaries

- Never expose provider keys to the dashboard.
- Never print or persist secrets.
- Never let model text directly execute emulator inputs.
- Never mutate production/cloud data from a model response without validation.
- Never use Master Balls for routine catches.
- Never evolve, trade, release, or overwrite the last required physical species copy.
- Never treat Pokédex flags as Living Dex ownership.
- Never guess RAM offsets.
- Checkpoint before risky action clusters.
- Keep live SaveRAM rollback/export paths.
- Keep paid workflows manual.

## Highest-Priority Gaps

### 1. Semantic RAM state

Discover and validate:

- battle active;
- map ID;
- player X/Y;
- facing;
- movement completion;
- transition/loading state;
- fishing state;
- catch result.

This single milestone eliminates a large amount of screenshot guessing.

### 2. Deterministic capture controller

Encode the proven flow:

```text
encounter -> identify target -> choose safe ball -> throw -> verify -> retry -> persist catch
```

Include:

- target/duplicate policy;
- party HP safety;
- ball ranking;
- no Master Ball rule;
- catch confirmation;
- PC-full handling;
- post-capture save/checkpoint.

### 3. Map graph and navigation primitives

Build verified nodes/edges for:

- Nuvema Town;
- Route 1 main path;
- Route 1 water landing;
- Accumula Town;
- Fly destinations;
- known Pokémon Center/PC anchors.

Store landmarks and movement sequences only after verification.

### 4. PC source-of-truth loop

After each catch:

1. export/read active SaveRAM safely;
2. parse party and PC;
3. confirm the species body exists;
4. update durable progress;
5. compute evolution reserves;
6. select the next route target.

### 5. Model benchmark harness

Extend dry routing benchmarks into live optional benchmarks measuring:

- provider/model;
- latency;
- token usage;
- schema compliance;
- invariant violations;
- validator acceptance;
- estimated cost.

Do not assume premium means correct. Pokémon menus have humbled greater intellects.

## Recommended Next Milestones

1. Commit the Basculin progress update and orchestrator work.
2. Build and smoke-test the Windows companion executable.
3. Add a deterministic fishing/capture macro with explicit timing parameters.
4. Persist Route 1 water-landing navigation as a verified landmark sequence.
5. Export/read SaveRAM and verify Basculin physically exists.
6. Mark Route 1 complete under the physical-inventory planner.
7. Select the next route target using missing species plus evolution reserves.
8. Resume RAM semantic discovery before broad autonomous travel.

## Validation Commands

```powershell
uv run ruff check .
uv run pyright
uv run pytest -q
uv run rld orchestrator-info
uv run rld provider-health
uv run rld model-router
uv run rld benchmark-routing
uv run rld serve --host 127.0.0.1 --port 8787
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_local_companion.ps1
.\dist\PokedexCompleterAgent.exe --scan-only
```

## Final Assessment

The repository is being used substantially, but not yet maximally. Its strongest assets are the physical save reader, emulator bridge, domain policies, API/MCP surfaces, and growing verified live gameplay knowledge. Its weakest link is semantic state, not model count.

The new orchestrator lets all configured model families contribute efficiently without turning the system into an expensive democracy of hallucinations. The executable and browser dashboard provide an interactive local product surface. The next autonomy leap comes from converting this session's supervised successes—Route 1 navigation, fishing, battle menu timing, and Basculin capture—into deterministic, tested, state-verified primitives.
