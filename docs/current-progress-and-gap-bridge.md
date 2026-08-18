# Current Progress and Gap Bridge: Bedroom to Autonomous Regional Dex Completion

Last updated: 2026-08-17

## Goal

Build a long-running autonomous Pokémon White completion machine that can:

1. Load the known save safely.
2. Resume into the player bedroom without accidentally selecting New Game.
3. Escape the house and reach the overworld route network.
4. Understand the current map/location and player position.
5. Read party/PC/save data to determine owned species.
6. Choose a missing regional Pokémon target that is catchable in this game.
7. Navigate to the target encounter area, using Fly when available and beneficial.
8. Catch one physical body of each needed species, prioritizing the regional dex/living-dex policy.
9. Recover safely when the game state is uncertain.

Current objective order, explicitly confirmed:

```text
1. Escape bedroom -> downstairs -> front door -> outside.
2. Re-read party + PC as the physical Living Dex source of truth.
3. Catch one of every wild-catchable species available in Pokemon White.
4. Check whether any party Pokemon knows Fly.
5. If not, teach Fly to a compatible owned Pokemon when possible.
6. If no compatible party Pokemon exists, inspect the nearest Pokemon Center PC.
7. If no compatible owned Pokemon exists, prioritize a nearby catchable flying/Fly-compatible species.
8. Use Fly-aware route planning for remaining wild catches.
9. Fill non-wild and missing evolution stages through evolution and breeding workflows.
```

The primary architecture must be generalized closed-loop gameplay:

```text
observe screenshot/state -> plan bounded actions -> execute one input -> re-observe -> correct
```

Room-specific grids and macros are optional learned/cache data, not the core agent. The agent must not blindly replay long input sequences when screenshots show lag, blocking, or overshoot.

The current save starts in the player's room in Nuvema Town.

```text
Bedroom -> stairs -> downstairs -> exit house -> Nuvema Town -> route network
```

From there, the machine needs location awareness and route planning.

## Current Known Good Capabilities

### Emulator lifecycle

We can launch BizHawk/melonDS with the Pokémon White ROM and Lua bridge.

Verified pieces:

- BizHawk launches through backend readiness.
- Lua bridge connects on native port `8766`.
- Backend health/readiness endpoints work.
- BizHawk speed is forced/configured to `400%`.
- SaveRAM is installed before launch.
- Current configured save source and SaveRAM hashes matched during verification.

Important save-safety note:

- The code currently leaves the save path as configured.
- The intended save data hash observed was:

```text
E7A706FEE023996987AEEA6FBE844A1101F1B8A00E87229B7A40C77D9765428D
```

### Input bridge

Controller input is working.

Known mappings:

```text
DS A       = keyboard X = confirm
DS B       = keyboard Z = cancel
DS X       = keyboard S = in-game menu
DS Start   = keyboard Enter
D-pad      = arrow keys
```

Observed working actions:

- Start advances title/menu flow.
- DS A confirms Continue.
- D-pad Down selects C-Gear `NO`.
- DS A confirms C-Gear prompts.
- DS X opens the Gen 5 overworld menu.
- Direction inputs move the player character.

### Safe resume from title

The title resume flow was hardened after a serious bug where the bot thought it was on the C-Gear prompt while actually still on the Continue menu. That caused:

```text
Down -> move selection from CONTINUE to NEW GAME
A    -> select NEW GAME
```

This is now guarded against.

Current safe flow:

1. Wait through boot/title/cinematic screens.
2. Press Start repeatedly until the real Continue menu is visually detected.
3. Confirm Continue with DS A / keyboard X.
4. Refuse to send C-Gear `Down + A` if still on Continue.
5. On C-Gear prompt:

```text
Down
wait
DS A / keyboard X
```

6. Confirm restricted C-Gear warning with DS A.
7. Verify final state with both visual and RAM evidence.

Recent verified resume invariant:

```text
status: candidate-overworld
visual_known_overworld: true
ram_verified: true
menu_open: false
menu_value: 4
```

### Visual guards

Current visual guards can distinguish several high-level states:

- boot/logo/blank-ish screens;
- real Continue menu with the blue save panel;
- dark intro/cinematic screens that must not be accepted as overworld;
- Gen 5 overworld-like frames with C-Gear lower screen.

The Continue detector was tightened to detect the actual blue/gray save panel, not merely a bright title screen.

### RAM-backed semantic scaffold

A profile-backed RAM semantic-state system exists:

```text
data/emulator_memory_profiles/white_us_eu.json
src/pokedex_completer_gen5/emulator/semantic_state.py
GET /api/emulator/semantic-state
```

Current trusted/tentative field:

```json
menu_state at ARM9 System Bus 0x020A84BF
```

Validated contextual values:

```text
4 or 6 -> menu closed / overworld-ish context
7      -> menu open
```

This is **not enough** to drive navigation. It only helps distinguish menu open/closed under known visual context.

### RAM discovery tooling

Existing tooling:

- `scripts/ram_discovery_matrix.py`
- `scripts/fast_ram_discovery.py`
- `scripts/menu_ram_cycle.py`
- `scripts/stable_ram_state_diff.py`
- `scripts/action_ram_checkpoint_diff.py`
- `scripts/paired_action_ram_diff.py`
- `scripts/validate_action_candidates.py`
- `scripts/timeline_action_candidates.py`

Important fix made:

The action diff tools originally saved timestamped checkpoint files but tried to reload by friendly checkpoint name. That meant scans drifted instead of restoring exact state. This was fixed so tools load the actual saved `.State` artifact path and require `ok: true` from load responses.

Contamination warning:

Any movement/RAM discovery outputs from before the fixed checkpoint-load logic, or before the title/Continue safety fixes, must be treated as contaminated unless rerun.

## Current Weak Point

Inputs move the character, but semantic tracking is not yet strong enough.

We do **not yet** have reliable offsets for:

```text
current map id
player X tile
player Y tile
facing direction
movement/transition completion
battle state
encounter state
```

This is the main bridge gap.

The bot can press buttons. What it cannot yet do reliably is know:

```text
Where am I?
Did I finish moving?
Which tile am I on?
Which map/route am I on?
Am I in battle?
Am I in a menu/dialog/transition?
```

Without those semantics, autonomous navigation would be button-spam with screenshots taped to it. Funny, but garbage.

## Immediate Bridge: Escape the Bedroom Reliably

The current known starting location is the player bedroom.

The first navigation bridge should be deliberately small:

```text
Goal: bedroom -> stairs -> downstairs
```

Then:

```text
downstairs -> house exit -> outside/Nuvema Town
```

### Why start here?

The bedroom is a controlled environment:

- known starting map visually;
- small room;
- few objects;
- stairs provide a clear map transition;
- no wild encounters;
- safe to checkpoint and retry.

### Required state signals for bedroom escape

Minimum viable signals:

1. Menu closed/open.
2. Movement complete / player controllable.
3. Map transition occurred.
4. Visual confirmation of downstairs or outside.

Ideal signals:

1. Map id.
2. X/Y tile position.
3. Facing direction.
4. Collision/blocked movement feedback.

### Practical first macro

A safe first version can be hybrid visual + RAM:

```text
checkpoint bedroom
ensure menu closed
execute short movement path toward stairs
wait for transition
verify screen changed to downstairs
if not verified, reload checkpoint and try corrected path
```

This is not final autonomy, but it creates a bridge out of the spawn room.

## RAM Discovery Plan

### Phase 1: Movement completion / controllable state

Find a stable byte/word that says:

```text
player is idle/control enabled
player is walking/transitioning/control disabled
```

Method:

1. Save checkpoint while idle in bedroom.
2. Sample candidate addresses before action.
3. Use `Wait`/idle as the control action.
4. Press movement directions as experimental actions.
5. Reject anything that changes identically on idle/control.
6. Repeat multiple cycles.
7. Promote only stable, movement-specific candidates.

Existing script:

```text
scripts/validate_action_candidates.py
```

Expected output ranking fields:

```text
baseline_stability
movement_change_rate
control_change_rate
movement_specific_change_rate
distinct_directional_after_modes
action_modes_different_from_control
```

Good candidate shape:

```text
baseline_stability ~= 1.0
movement_change_rate high
control_change_rate == 0.0
movement_specific_change_rate > 0.0
```

Bad candidate shape:

```text
changes on Wait/control
baseline drifts
changes identically for every action including no-op/control
unchanged stable bytes that only look good because they are boring
```

Current discovery notes from 2026-08-17:

```text
scripts/validate_action_candidates.py now supports:
- batched nearby RAM reads via /api/emulator/memory/read-bytes
- true idle control action: Wait
- --control-action
- --range START LENGTH for focused neighborhood validation
- compact stdout summaries while preserving full JSON output

scripts/timeline_action_candidates.py now supports:
- checkpointed per-action RAM timelines
- configurable sample frames after press/tap
- longer pre-checkpoint settling to reduce non-idle checkpoint contamination
- ranking by action-vs-idle divergence over time instead of one after-snapshot
```

Recent validation artifacts:

```text
.runtime/ram-validation/20260817T020327Z-candidate-validation.json
  range: 0x2146924 length 0x200 around 0x2146A24
  result: weak/noisy only; 0x2146A24 changes on Wait/control and is not a clean semantic byte

.runtime/ram-validation/20260817T021250Z-candidate-validation.json
  range: 0x214BC00 length 0x400
  result: several action-specific candidates, but many did not survive shortlist validation

.runtime/ram-validation/20260817T021638Z-candidate-validation.json
  range: 0x214CC00 length 0x600
  result: many hot 0x214CFxx candidates looked promising in 2 cycles but later collapsed as control/time-like bytes

.runtime/ram-validation/20260817T022428Z-candidate-validation.json
  shortlist: 5 cycles across combined hot candidates
  result: most candidates rejected; mild remaining leads are 0x214BC97 and 0x214D0F2
```

Current shortlist interpretation:

```text
0x214BC97:
  baseline_stability=1.0
  movement_change_rate=0.3
  control_change_rate=0.0
  movement_specific_change_rate=0.3
  action_after_modes: Down=4, Left=1, Right=1, Up=1, Wait=1

0x214D0F2:
  baseline_stability=1.0
  movement_change_rate=0.25
  control_change_rate=0.0
  movement_specific_change_rate=0.25
  action_after_modes: Down=1, Left=1, Right=1, Up=3, Wait=1
```

These are not strong enough to promote into the RAM profile yet. They are leads for more controlled probes, not verified offsets. The highly-ranked `0x214CFxx` bytes are currently suspected transition/timer/control artifacts because they changed identically or near-identically under `Wait` in the 5-cycle shortlist.

Tiny-tap facing probe update:

```text
.runtime/ram-validation/20260817T023332Z-candidate-validation.json
  shortlist: 0x214BE10, 0x214BFB5, 0x214BF69, 0x214BF6C, 0x214CF01, 0x214CF04, 0x214CF10, 0x214CF15
  method: press_frames=2, advance_frames=25, cycles=5, Wait control
  result: facing-like leads collapsed; no candidate is reliable enough for profile promotion
```

Interpretation:

```text
Tiny directional taps are still changing lots of transient/control/timer-like bytes.
The next probe should either:
1. find/force a truly idle checkpoint and sample longer before saving it; or
2. use visual tile/facing confirmation plus RAM timelines to distinguish transient animation bytes from semantic facing/position bytes.
```

A first timeline run was started with:

```text
scripts/timeline_action_candidates.py \
  0x214BC97 0x214D0F2 0x2146A24 0x214BE10 0x214BFB5 0x214BF69 0x214BF6C \
  0x214CF01 0x214CF04 0x214CF10 0x214CF15 0x214CFC5 0x214CFF6 \
  --cycles 3 \
  --actions Up Down Left Right \
  --checkpoint timeline-hot-leads-1 \
  --press-frames 8 \
  --sample-frames 0 5 10 20 40 80 120 180 240 \
  --settle-frames 60 \
  --pre-checkpoint-settle-frames 240 \
  --no-ensure-ready
```

Do not interpret this until its `.runtime/ram-validation/*-timeline-validation.json` artifact exists and is reviewed.

### Phase 2: Facing direction

Use short taps that turn the player without moving a tile when possible.

Method:

```text
load checkpoint
press Up for tiny frame count
wait short
sample candidates
repeat for Down/Left/Right
```

A facing field should:

- not change on `Wait`/idle control;
- have stable baseline;
- map to one of four values after directional taps;
- not require full tile movement.

### Phase 3: X/Y tile position

Once movement completion is known:

1. Start from checkpoint.
2. Perform one successful tile step.
3. Wait until idle.
4. Compare pre/post RAM.
5. Repeat in directions where movement is not blocked.

Good X/Y candidate shape:

```text
Up/Down changes Y-related value
Left/Right changes X-related value
opposite directions change in opposite signs or nearby values
B does not change either
baseline stable after checkpoint reload
```

### Phase 4: Map id

Use known transitions:

```text
bedroom -> downstairs
house -> Nuvema Town
Nuvema Town -> Route 1
```

A map id candidate should:

- remain stable during walking on the same map;
- change after transition;
- not change from menu open/close;
- not change from facing-only taps.

## Automation Plan: From Bedroom to Route

### Step A: Current-safe resume

Always begin with:

```text
ensure-ready
resume-save-from-title
verify candidate-overworld
save checkpoint: known-room-start
```

Never continue if:

- Continue menu still visible after A;
- visual overworld guard fails;
- RAM menu state is not closed/open-known;
- bridge disconnected;
- any C-Gear prompt is not visually/semantically expected.

### Step B: Exit bedroom

Build a supervised macro first:

```text
close menu if open
walk to stairs
wait for downstairs transition
verify downstairs visually
save checkpoint downstairs
```

This should be separate from general pathfinding. YAGNI: do not write a full navigation engine before proving one room transition.

### Step C: Exit house

From downstairs checkpoint:

```text
walk to door
trigger exit
verify outside/Nuvema Town
save checkpoint outside-house
```

### Step D: Determine current route/location

Preferred solution:

```text
RAM map_id + X/Y
```

Fallback during discovery:

```text
visual scene classifier + known transition graph
```

Once outside, begin building a small map graph:

```text
Nuvema Town
Route 1
Accumula Town
Route 2
Striaton City
...
```

## Dex Completion Plan

### Save/PC/party source of truth

The project should not trust Pokédex flags as completion proof.

Source of truth:

```text
physical Pokémon in PC boxes + party
```

Use save parsing/report commands to compute owned species inventory.

Target policy:

```text
one physical body of each regional species available in Pokémon White
```

### Target selection

For each missing species:

1. Check if available in Pokémon White without trading/event-only requirements.
2. Determine earliest/best catch locations.
3. Consider encounter rate, season/time restrictions, required HMs, and story gating.
4. Choose the highest priority target.

Basic priority heuristic:

```text
available now > high encounter rate > nearby > low risk > unlocks future traversal/evolution utility
```

### Party utility checks

Before route planning, inspect party for traversal moves:

```text
Fly
Surf
Strength
Cut
Waterfall
```

Current requested important case:

```text
Does a current party Pokémon know Fly?
```

If yes:

1. Read known Fly destination flags/visited towns if possible.
2. Use Fly as an edge in the travel graph.
3. Choose shortest path to target route/location.

If no:

1. Use walking graph only.
2. Consider whether obtaining/teaching Fly is itself a prerequisite task.

### Navigation graph

Represent travel as weighted edges:

```text
node: map/location
edge: walking transition, gate, cave door, route connector, Fly destination
cost: expected traversal time + encounter risk + required capabilities
```

Example:

```text
Nuvema Town -> Route 1: walk north
Nuvema Town -> Player House: door transition
Any outdoor map -> Fly destination: if Fly known + destination unlocked
```

### Catch execution loop

For a chosen target:

1. Navigate to encounter location.
2. Walk encounter pattern in grass/cave/water.
3. Detect battle start.
4. Identify encountered species.
5. If target species:
   - weaken safely if needed;
   - throw Poké Ball class based on inventory/strategy;
   - verify caught;
   - update owned inventory.
6. If not target:
   - run/KO safely;
   - continue encounter loop.
7. Check party/box capacity and healing/resource needs.

## Recovery and Safety Rules

The bot must checkpoint before risky clusters:

```text
before leaving known map
before entering grass encounter loop
before using limited resources
before battle capture sequence
before menu-heavy operations
```

Never continue if state is unknown and irreversible actions could happen.

Hard stop cases:

- Continue/New Game menu ambiguity.
- Dialog/menu where selected item is unknown.
- Low health and unknown battle state.
- Save write or in-game save operation not explicitly approved.
- Party full/PC full ambiguity.
- Out of balls during capture loop.

## Next Concrete Milestones

### Milestone 1: Reliable bedroom escape macro

Deliverable:

```text
POST /api/emulator/macro/escape-bedroom
```

Behavior:

- assumes currently in verified bedroom overworld;
- checkpoints before moving;
- walks to stairs;
- verifies downstairs visually/semantically;
- returns `candidate-downstairs` or `needs-human`.

### Milestone 2: Downstairs-to-outside macro

Deliverable:

```text
POST /api/emulator/macro/exit-house
```

Behavior:

- starts from downstairs;
- walks to door;
- verifies outside/Nuvema Town;
- checkpoints outside.

### Milestone 3: Movement state RAM field

Deliverable:

```json
transition_state or movement_state in white_us_eu.json
```

Must be backed by repeated validation evidence.

### Milestone 4: Map id discovery

Deliverable:

```json
map_id in white_us_eu.json
```

Validated across:

```text
bedroom
downstairs
Nuvema Town
Route 1
```

### Milestone 5: Player position/facing discovery

Deliverable:

```json
player_x
player_y
facing
```

Validated by checkpointed movement cycles.

### Milestone 6: Route graph and target planner

Deliverable:

```text
location graph + target chooser
```

Inputs:

- owned species from PC/party save parsing;
- catchability database;
- party HMs/moves, especially Fly;
- current map/position.

Output:

```text
next target species
best catch location
navigation plan
required resources
```

## Current Status Summary

We are no longer stuck at the title screen. We are safely loading into the save and can move the player in the bedroom.

Current blocker:

```text
The bot can move, but does not yet have reliable map/X/Y/facing/movement-complete RAM semantics.
```

Immediate next task:

```text
Validate movement/position/facing candidates, then build the first bedroom escape macro.
```

Once bedroom escape works, we can chain:

```text
bedroom -> downstairs -> outside -> route identification -> target selection -> navigation -> encounter/catch loop
```

That is the bridge from today's emulator-control work to the actual regional Pokédex completer.
