# Safety and Policy

## Save handling

- Default mode is read-only.
- No save writing in MVP.
- Future save writing must be opt-in, backed up, checksummed, and tested.
- PKHeX.Core may be used as an auditor/verifier, not as the gameplay mechanism for creating Pokémon.

## Living Dex preservation

Never perform actions that can destroy Living Dex completeness without explicit user confirmation.

Forbidden by default:

- release Pokémon;
- evolve the last required copy of a stage;
- trade away a last required copy;
- overwrite save data;
- consume one-time resources without checkpoint;
- box operations that lose track of physical bodies.

## Emulator automation

- Must be interruptible.
- Must checkpoint before risky operations.
- Must pause on uncertainty.
- Must log actions and observations.
- Must not blindly run if state decoder and visual state disagree.

## AI behavior

The LLM chooses objectives and recovery strategies.

The LLM should not be the frame-by-frame joystick for normal operation.

Computer-use / screenshot-driven behavior is allowed for:

- fallback;
- debugging;
- demos;
- supervised data collection;
- unknown-state recovery.

## ROM / copyright note

This project should not distribute ROMs, BIOS files, copyrighted game assets, or proprietary save files.

Users must provide their own legally obtained game files and saves.
