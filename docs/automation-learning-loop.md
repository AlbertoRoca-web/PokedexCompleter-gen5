# Automation, AI, and Learning Loop

The emulator bridge proves we can observe and press buttons. The AI does **not** become the joystick gremlin. It should plan, explain, rank options, and review failures while deterministic code executes verified actions.

## Layers

1. **State collectors**
   - save parser: PC/party/living dex state
   - emulator bridge: current frame/control ability
   - future memory readers: map, coordinates, menu mode, battle state

2. **Deterministic macros**
   - `open_menu`: press Gen 5 `menu` action, which maps to NDS `X` / default keyboard `S`
   - `close_menu`: press cancel / `B`
   - `advance_dialogue`: press confirm / `A` with frame gaps
   - future: route walking, box management, battle capture, repel loop

3. **Planner**
   - deterministic planner builds candidate next tasks from missing Living Dex targets
   - AI provider may rank/explain those tasks, but cannot bypass validators

4. **Validator**
   - checks whether claimed progress is real
   - compares before/after save state, emulator state, and event logs
   - rejects impossible or unsafe action proposals

5. **Learning feedback loop**
   - every attempted macro emits an event: context, action, expected result, observed result
   - failed macros become training labels / tuning examples
   - planner uses local history to avoid repeating bad route/menu assumptions

## Recursive feedback loop shape

```text
observe -> plan -> propose macro -> validate preconditions -> execute -> observe -> score -> store -> improve planner hints
```

Rules:

- The loop must be bounded. No infinite autonomous recursion. Tiny puppy does not become Skynet.
- Every action has a timeout, checkpoint, and rollback plan.
- AI suggestions are advisory until deterministic validators accept them.
- Voice commentary is separate and does not directly control the emulator.

## First practical automation target

Now that native BizHawk control works, the first macro should be tiny:

```text
open_menu:
  action: menu
  NDS button: X
  default keyboard: S
  expected result: Pokemon pause menu appears
```

Then:

```text
close_menu:
  action: cancel
  NDS button: B
  default keyboard: Z
```

After these are stable, build higher-level macros from them. Do not write a giant universal bot first. That would be spaghetti with a hat.
