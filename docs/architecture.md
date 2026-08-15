# Architecture

## Recommendation

Build a hybrid emulator agent:

```text
Structured state first -> deterministic macros -> vision fallback -> LLM planner
```

Do not build the core loop as:

```text
screenshot -> LLM -> one button -> screenshot -> LLM -> one button
```

That loop is slow, expensive, brittle, and frankly has big “teaching a Magikarp calculus” energy.

## Layers

```text
User / Dashboard
        |
        v
Dex Goal Engine
        |
        v
LLM Planner
        |
   MCP / REST tools
        |
        v
Pokemon Agent API
   |              |
Action Engine    State Decoder
   |              |
   v              v
BizHawk Lua Bridge
        |
        v
BizHawk + melonDS
        |
        v
Pokemon Black / White / Black 2 / White 2
```

## Responsibilities

### Save / state layer

- Decode PK5 Pokémon records.
- Read PC + party physical bodies.
- Read emulator RAM through BizHawk Lua.
- Provide structured state JSON.

### Dex engine

- Count physical Living Dex bodies.
- Track missing required stages.
- Apply rulesets for obtainability.
- Generate tasks: catch, breed, evolve, trade, obtain item, static encounter, event-only.

### Deterministic executor

- Navigate known maps.
- Advance dialogue.
- Run/capture battle flows.
- Use menus.
- Manage PC boxes safely.
- Save/checkpoint/recover.

### LLM planner

The LLM should reason over objectives, not buttons.

Good:

```text
Acquire Solosis using Route 5 encounter plan.
```

Bad:

```text
Press left. Press left. Press up. Press A. Press A. Press A.
```

### Vision fallback

Use screenshots for:

- recovery from unknown state;
- validating state decoder bugs;
- collecting supervised labels;
- demo mode;
- OCR where memory decoding is not yet known.

## Protocols

Expose the Python service through both:

- REST/WebSocket for dashboards, tests, scripts, and RL;
- MCP for AI agents.

## Agent tool surface

Keep model-facing tools semantic:

```text
get_state()
get_dex_status()
get_missing_species()
get_acquisition_plan()
navigate_to(location)
capture_species(species)
evolve_species(species)
organize_boxes()
save_checkpoint(label)
restore_checkpoint(label)
recover_from_stuck()
```

Raw memory tools should exist only in developer/debug mode.
