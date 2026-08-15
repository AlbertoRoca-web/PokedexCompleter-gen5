# Catchable Inventory Completion

This is the core product direction.

The app should not rely on Pokédex caught/seen flags. A completed game can have a completed Pokédex while the PC boxes do not contain every target species as physical bodies.

## Source of truth

Use:

```text
active save copy -> active PC boxes + party -> physical species inventory
```

Do not use:

```text
Pokédex flags
seen flags
caught flags
trainer card completion
```

## Goal

For the detected/selected game, build a target list of species that can be directly caught or otherwise obtained in that game, then compare against physical PC/party inventory.

Current CLI:

```powershell
uv run rld catchable-report "D:\path\to\POKEMON W.sav" --game white --mode direct
```

Modes:

```text
direct      directly catchable/static/roamer/story encounters, no trade/event/transfer
obtainable  gifts/fossils/eggs in addition to direct encounters
```

```powershell
uv run rld catchable-report "D:\path\to\POKEMON W.sav" --game white --mode obtainable
```

## Current limitations

- Game auto-detection from save internals is not implemented yet; use `--game`.
- Black 2 / White 2 target data is still pending.
- Encounter locations/routes are not fully structured yet.
- Current target classification is based on explicit BW data method strings.

## Privacy

Reports compare species IDs/counts. Save files are read locally. Do not upload save blobs by default.
