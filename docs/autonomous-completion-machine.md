# Autonomous Completion Machine

End goal: a durable Gen 5 Living Dex completer that can run for a long time, bounded by wallet/tokens, emulator stability, and explicit safety budgets.

The machine is not one giant prompt. It is a supervised loop:

```text
observe -> plan -> validate preconditions -> act -> verify -> persist -> recover -> repeat
```

## Current bridge status

| Bridge | Status | Notes |
| --- | --- | --- |
| Save parser | Built | Can report PC/party and regional Living Dex gaps. |
| BizHawk launch | Built | Can install configured White save and launch with Lua. |
| Native Lua bridge | Built | Press/frame/screenshot/checkpoint/memory reads. |
| Fast-mode timing | Built | Defaults assume max-speed, observation-driven actions. |
| QA kitten | Built | Headed/headless Playwright dashboard/emulator smoke loop. |
| Backend restart discipline | Built | Kills old CMD/process tree before launching fresh backend. |
| Title resume macro | Built | Visual candidate-overworld validation. |
| RAM probe script | Built | Can diff RAM before/after actions. |
| Semantic emulator state | Missing | Need RAM-backed mode/menu/battle/map/player coordinates. |
| Safe navigation primitives | Missing | Need validated step/turn/interact/menu primitives. |
| Encounter detection | Missing | Need battle/species/shiny/catch-result detection. |
| Capture loop | Missing | Need deterministic ball/menu workflow and verification. |
| PC/box automation | Missing | Need deposit/withdraw/box navigation and verification. |
| Target planner | Partial | Save report exists; route/acquisition graph missing. |
| Recovery policy | Partial | Readiness exists; action-level rollback/checkpoint policy missing. |

## Long-running requirements

The loop must support:

- explicit time/iteration/token budgets;
- dry-run mode;
- durable event logs;
- checkpoints before risky action clusters;
- retry limits and backoff;
- validator gates before planner claims progress;
- memory-backed state where possible;
- screenshot fallback when memory is unknown;
- no unbounded button spam;
- post-push backend restart from current code.

## Immediate build order

1. Discover RAM-backed semantic state:
   - menu open/closed;
   - battle active;
   - map ID;
   - player X/Y/facing;
   - transition/loading flag.
2. Implement `GET /api/emulator/semantic-state` from a versioned RAM profile.
3. Upgrade title/menu macros to require semantic-state verification when available.
4. Build safe navigation primitives.
5. Connect missing-dex targets to acquisition route data.
6. Build encounter and capture loops.
7. Build PC verification/deposit workflow.
8. Let the autonomy supervisor execute one validated primitive per iteration.

## Useful commands

Run the supervisor scaffold:

```bash
uv run rld autonomous-run --max-iterations 3 --max-seconds 30
```

Probe RAM around a range:

```bash
uv run python scripts\ram_probe.py --domain "ARM9 System Bus" --address 0x02000000 --length 65536 --press Start --advance-frames 120
```

Restart backend after code changes:

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_backend_window.ps1
```
