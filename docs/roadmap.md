# Roadmap

## Phase 0 — migrate prototype

Source prototype:

```text
D:\alroc\codepup\Scripts\regional-pokedex-completer
```

Tasks:

- move code into `src/pokedex_completer_gen5/`;
- add CLI entry points;
- add tests;
- add JSON report output; initial `--format json` implemented;
- keep prototype behavior read-only.

## Phase 1 — stable Gen 5 save extraction

Tasks:

- formalize PK5 decoder;
- formalize BW/B2W2 save layout;
- detect active save copy using real counters/checksums;
- extract party and PC boxes;
- produce physical body reports;
- test Black, White, Black 2, White 2 fixtures.

Success condition:

```text
rld inspect-save save.sav --game white --format json
```

returns correct physical bodies without writing to the save.

## Phase 2 — BW regional Living Dex planner

Tasks:

- finish Black/White Unova 156-entry planner;
- evolution levels/items/trades;
- breedability and Ditto constraints;
- version exclusives;
- obtainability rulesets;
- route/location/action hints.

Success condition:

```text
rld report-living-dex POKEMON W.sav --game white
```

returns a correct Living Dex task plan.

## Phase 3 — B2W2 regional Living Dex planner

Tasks:

- add Black 2 / White 2 regional dex; skeleton module exists at `dex/b2w2_unova.py`;
- B2W2 routes/location data;
- B2W2 version exclusives;
- B2W2 obtainability rules;
- ensure B2W2 never uses BW dex data.

## Phase 4 — REST/WebSocket server

Tasks:

- FastAPI service;
- `/state`;
- `/dex`;
- `/report`;
- `/tasks`;
- `/screenshot` placeholder;
- WebSocket telemetry stream.

## Phase 5 — MCP server

Tasks:

- expose semantic agent tools;
- support local LLM/agent clients;
- keep raw memory tools developer-only.

## Phase 6 — BizHawk Lua bridge

Tasks:

- launch BizHawk + melonDS target;
- Lua bridge scaffold exists at `lua/bizhawk_gen5_bridge.lua`;
- Lua bridge for memory read/write-safe inputs;
- Python client;
- screenshots;
- save/load checkpoints;
- frame advance;
- button/touchscreen sequences.

## Phase 7 — structured game state

Decode:

- map id;
- player x/y;
- facing direction;
- current mode;
- party;
- PC;
- inventory;
- battle opponent;
- legal actions.

## Phase 8 — deterministic macros

Implement:

- navigate;
- advance dialogue;
- heal;
- restock;
- encounter search;
- battle/capture policy;
- daycare/breeding workflow;
- safe PC management.

## Phase 9 — LLM planner

Tasks:

- objective selection;
- tool calling through MCP;
- verifier loop;
- recovery loop;
- cost/reliability tracking.

## Phase 10 — supervised learning / vision fallback

Tasks:

- screenshot capture dataset;
- labeling UI;
- screen-state classifier;
- OCR fallback;
- active learning loop;
- optional Hugging Face model/dataset.

## Phase 11 — optional RL

Tasks:

- Gymnasium environment;
- narrow navigation/battle policies;
- benchmark against deterministic macros.
