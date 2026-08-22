# Supervised Autonomy First Pass

Last updated: 2026-08-22

## Purpose

This runbook is the operating procedure while semantic RAM state, navigation, battle detection, capture verification, and PC automation are incomplete.

Alberto is the supervising game expert. The agent controls the project mechanisms, proposes one bounded action at a time, observes results, records corrections, and promotes only repeatable behavior into code.

The goal is not to pretend the game is autonomous before it is. The goal is to turn supervised success into deterministic, tested primitives.

## Canonical Loop

```text
observe
-> identify current screen and known landmark
-> choose one objective
-> validate safety and preconditions
-> checkpoint before risky action clusters
-> execute one bounded primitive
-> capture a fresh screenshot/state
-> verify the actual result
-> ask Alberto when visual meaning is ambiguous
-> persist correction and evidence
-> repeat
```

## Hard Rules

1. Never execute multiple uncertain directional guesses as a batch.
2. Never claim an action succeeded from intent alone.
3. Never overwrite Alberto's confirmed gameplay fact with an incomplete machine detector.
4. Never use a Master Ball for a routine encounter.
5. Never evolve, trade, release, or overwrite the last required physical species copy.
6. Never treat Pokédex flags as Living Dex ownership.
7. Never guess RAM offsets.
8. Never let an LLM response directly execute emulator controls.
9. Never continue after an unexpected battle, menu, dialogue, transition, faint, or disconnect without observing again.
10. Prefer project REST/MCP/CLI mechanisms over ad-hoc input hacks.

## Evidence Hierarchy

Use evidence in this order:

1. Save-file physical party/PC extraction.
2. Verified semantic RAM fields.
3. Fresh emulator screenshot plus known screen/landmark rules.
4. Alberto's direct supervised confirmation.
5. Model interpretation.

Machine verification and supervised truth are complementary. If Alberto confirms a catch while save extraction is not yet refreshed, record the catch as confirmed and separately track save verification as pending. Do not demote the catch back to “maybe.”

## Current Confirmed Progress

- The known Pokémon White save loads safely.
- The player escaped the bedroom/house and reached Route 1.
- Patrat was caught.
- Lillipup was caught.
- Evolution-reserve planning prevents redundant Watchog targeting.
- Super Rod was registered in the quick-select menu.
- The valid Route 1 water landing was discovered by moving west/left across the red-railed stair passage.
- A female level-36 Basculin was hooked with the Super Rod.
- Basculin was caught after safe ball retries.
- Current verified landmark: Route 1 rectangular pond, player on the east bank facing west, overworld active, menu closed.

## Current Machine Limitations

The following fields remain unknown or tentative:

- battle active;
- map ID;
- player X/Y;
- facing in RAM;
- transition/loading state;
- movement completion;
- fishing state;
- encountered species;
- catch-result state.

The tentative menu-state byte can distinguish known closed/open values but must not be treated as complete semantic state.

## Action Classes

### Read-only observation

Safe without additional confirmation:

- health and bridge diagnostics;
- emulator state and semantic-state reads;
- screenshots;
- telemetry and trajectory reads;
- save report generation from copied/exported data;
- provider health and orchestrator capability checks.

### Bounded reversible action

Execute one at a time, then observe:

- one directional tap/pulse;
- one A/B/X/Start interaction;
- opening or closing a known menu;
- selecting a registered item from a verified menu;
- one battle-menu selection;
- one short frame advance;
- saving a checkpoint.

### Risky action cluster

Checkpoint and obtain/retain supervision:

- route transitions;
- multi-step menu macros;
- fishing attempts;
- encounter handling;
- throwing balls;
- party/PC modification;
- evolution;
- item consumption with scarce inventory;
- save/checkpoint loading;
- any recovery from an unknown screen.

## Navigation Procedure

For each move:

1. Capture the current screen.
2. Name the visible landmark.
3. State the desired adjacent landmark or orientation.
4. Execute one short directional primitive.
5. Capture another screen.
6. Classify the result:
   - moved;
   - turned only;
   - blocked;
   - transition;
   - encounter;
   - unknown.
7. Record Alberto's correction if classification or direction was wrong.
8. Promote the sequence only after repeatable success.

Do not issue long direction sequences while map coordinates are unknown.

## Fishing Procedure

Known Route 1 supervised flow:

```text
stand at verified east bank
face west toward water
checkpoint
open registered-item quick menu
select Super Rod
wait for bite
confirm within approximately 10–15 seconds under current lag
observe encounter
classify species/duplicate policy
catch or flee safely
verify overworld return
persist result
```

Important details:

- The decorative/cliff-banked pond edges are not all valid fishing banks.
- The current rectangular pond east bank is a verified valid landing.
- Registered-item activation still requires selecting Super Rod from the quick menu.
- Four-frame menu taps have often been more reliable than long holds.
- Ten-frame overworld movement can be lost under lag; always verify visually.

## Battle and Capture Procedure

```text
observe battle screen
-> identify target and party safety
-> decide catch/flee
-> checkpoint if appropriate
-> open Bag
-> select Poké Balls pocket
-> select safe ball
-> choose Use
-> wait for complete animation/text
-> capture fresh screenshot
-> if caught, accept supervised confirmation and persist
-> if escaped, reassess HP/balls and retry budget
-> if unexpected state, stop and recover
```

Ball policy:

- never routine-use Master Ball;
- prefer Repeat Ball for previously registered species where appropriate;
- prefer Net Ball for Water/Bug targets where appropriate;
- preserve scarce/special balls when a common ball is sufficient;
- stop after bounded retries if party or inventory safety changes.

## Party/PC Cross-Reference Procedure

Target and route selection must use physical bodies from both sources:

```text
party bodies
+ PC box bodies
+ verified unsaved/session catches
-> species counts
-> evolution-family reserve quotas
-> missing direct targets
-> route/location grouping
-> Fly versus walking decision
```

The save parser is the deterministic PC cross-reference. Opening the in-game PC is still required later for depositing, withdrawing, box organization, and visually supervised verification, but route planning must not depend on manually browsing every box when the save parser can read all slots safely.

After every true in-game save, export live SRAM, parse party plus PC, and refresh the master route cross-reference before selecting the next target.

## Persistence Procedure

After a confirmed acquisition:

1. Record species, level/form/sex if known, location, method, and supervised confirmation.
2. Capture an overworld or result screenshot.
3. Save a named checkpoint.
4. Export/read SaveRAM when practical.
5. Confirm the physical body in party or PC.
6. Recompute missing species and evolution reserves.
7. Select the next target.

A pending save verification is a verification task, not a reason to erase supervised catch truth.

## Correction Procedure

When Alberto corrects the agent:

1. Stop issuing controls.
2. Restate the corrected fact plainly.
3. Update the relevant runbook, knowledge JSON, policy, test, or progress record.
4. Explain the next single action.
5. Resume only from a fresh observation.

Corrections are training data for deterministic behavior, not conversational trivia.

## Recovery Procedure

Stop and observe when:

- the screen differs from the predicted postcondition;
- input appears ignored;
- the player loops between landmarks;
- a battle starts unexpectedly;
- the bridge disconnects;
- the menu lane is uncertain;
- party safety is unknown;
- the checkpoint label/path is unclear.

Recovery order:

```text
fresh screenshot
-> semantic state
-> bridge diagnostics
-> identify known landmark/screen
-> use B only when safe to unwind menus/dialogue
-> load checkpoint only with explicit rollback intent
```

## Promotion to Automation

A supervised sequence becomes code only when it has:

- named preconditions;
- bounded inputs;
- expected screenshots or semantic postconditions;
- retry limits;
- failure exits;
- checkpoint policy;
- telemetry;
- at least one test;
- Alberto-confirmed behavior.

Avoid one-off scripts when the behavior belongs in an existing domain module. Keep macros semantic and reusable.

## Next Safe Milestones

1. Save a named checkpoint at the current Route 1 water landing. **Completed.**
2. Persist the landmark and Basculin catch in durable progress/knowledge data. **Completed.**
3. Export/read current SaveRAM and confirm Basculin physically exists. **Completed:** Box 01 Slot 20.
4. Recompute the regional Living Dex target report. **Completed:** 11/143 regional targets physically owned; 132 missing.
5. Choose the next target using missing species and evolution reserves. **Completed:** Fly to Dreamyard; Route 1 Audino is deferred until shaking-grass detection is reliable.
6. Supervise travel to Dreamyard one bounded primitive at a time.
7. Implement and test a deterministic fishing/capture controller from the recorded flow.
8. Continue RAM semantic discovery alongside gameplay, especially battle and movement state.

## Session Start Checklist

At the beginning of every supervised session:

```text
read this runbook
read latest progress document/data
check git status
check backend health
check native bridge diagnostics
capture fresh screenshot
read semantic state
name current landmark/screen
state one next objective
checkpoint before risky actions
```

## Session End Checklist

```text
capture final screenshot
save named checkpoint
record confirmed progress and corrections
update durable knowledge/policy if needed
run tests for changed code
commit and push cohesive repository changes
state exact current game location and next action
```
