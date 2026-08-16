# PokedexCompleter Gen 5

AI-assisted **Generation 5 PC Living Dex completer** for Pokémon Black / White / Black 2 / White 2.

The project goal is not to trust Pokédex caught/seen flags. A completed Pokédex is just game flags. A Living Dex means physical Pokémon bodies living in the PC, with party optionally counted as currently owned. The source of truth is active save copy -> PC boxes + party -> physical species inventory.

## Core philosophy

```text
Structured state first.
Deterministic macros second.
Vision as fallback.
LLM as planner, not joystick.
```

The save file / emulator memory should be the source of truth. Screenshots are useful for recovery, demos, and supervised learning, but the main control loop should not ask an LLM to press one button at a time forever. That would be expensive, slow, and extremely silly.

## Target architecture

```text
LLM Planner / Agent
        |
      MCP tools
        |
FastAPI + MCP Python service
        |
Pokemon-specific state/actions
        |
BizHawk Lua bridge
        |
BizHawk + melonDS core
        |
Pokemon Gen 5 game
```

## Current planned stack

- Python 3.12+
- FastAPI for REST/WebSocket API
- MCP for AI-agent tool protocol
- BizHawk + melonDS Nintendo DS core
- Lua bridge for emulator memory/input/checkpoints
- Pydantic for schemas
- SQLite locally for run history
- Optional Supabase for cloud sync / labels / reports
- Optional Hugging Face Spaces for demo/model hosting
- PokéAPI as metadata source
- Local Gen V acquisition rules database
- PKHeX.Core as auditor/verifier, not as a Pokémon generator
- Gymnasium later for RL-compatible environments

## Immediate status

A prototype exists outside this repo under:

```text
D:\alroc\codepup\Scripts\regional-pokedex-completer
```

That prototype already has:

- read-only PK5 decoding;
- party + PC extraction for observed Gen 5 saves;
- BW Unova living dex planner prototype;
- physical PC/party inventory extraction;
- catchable-target report path;
- breeding shortcut logic;
- game profile guardrails so B2W2 does not silently use BW dex data.

Next step is migrating that prototype into this repo as a proper package.

## Safety rules

- Default mode is read-only.
- No save writing until offsets, checksums, rollback, and tests are proven.
- Never silently apply the wrong regional dex to a game.
- Never evolve/release/trade away the last required physical inventory copy.
- Emulator automation must be interruptible.
- LLMs choose objectives; deterministic executors perform repetitive actions.

## Docs

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/ai-planner.md`](docs/ai-planner.md)
- [`docs/bizhawk-smoke-test.md`](docs/bizhawk-smoke-test.md)
- [`docs/catchable-inventory.md`](docs/catchable-inventory.md)
- [`docs/tech-stack.md`](docs/tech-stack.md)
- [`docs/roadmap.md`](docs/roadmap.md)
- [`docs/safety.md`](docs/safety.md)
- [`docs/automation-learning-loop.md`](docs/automation-learning-loop.md)
- [`docs/emulator-api.md`](docs/emulator-api.md)
- [`docs/fixtures.md`](docs/fixtures.md)
- [`docs/github-setup.md`](docs/github-setup.md)
- [`docs/pc-living-dex.md`](docs/pc-living-dex.md)
- [`docs/provider-health.md`](docs/provider-health.md)
- [`docs/supabase.md`](docs/supabase.md)
- [`docs/supabase-persistence.md`](docs/supabase-persistence.md)
- [`docs/voice-copilot.md`](docs/voice-copilot.md)

## Development

Planned install flow:

```powershell
uv sync
uv run rld --help
```

Planned CLI examples:

```powershell
rld inspect-save "D:\path\to\POKEMON W.sav" --game white
rld pc-living-dex "D:\path\to\POKEMON W.sav" --game white --scope regional --target-policy game-regional
rld catchable-report "D:\path\to\POKEMON W.sav" --game white --mode direct
rld report-living-dex "D:\path\to\POKEMON W.sav" --game white --format markdown
rld report-living-dex "D:\path\to\POKEMON W.sav" --game white --format json
rld provider-health
rld sync-report "D:\path\to\POKEMON W.sav" --game white
rld plan-report report.json --provider openai
rld serve --host 127.0.0.1 --port 8787

# BizHawk bridge scaffold lives under lua/bizhawk_gen5_bridge.lua
# Manual bridge smoke test: docs/bizhawk-smoke-test.md
```

## License

See [`LICENSE`](LICENSE).
