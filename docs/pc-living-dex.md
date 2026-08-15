# PC Living Dex

A completed Pokédex is a set of game flags.

A Living Dex is physical Pokémon bodies organized in storage. For this project, the default goal is:

```text
Regional Unova Living Dex in the PC, with party optionally counted as currently owned.
```

The source of truth is:

```text
active save copy -> PC boxes + party -> physical species inventory
```

Not:

```text
Pokédex seen/caught flags
trainer card completion
```

## Local website

Run:

```powershell
uv run rld serve --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787/
```

The dashboard lets you enter a local save path, choose game/scope, and view missing PC Living Dex targets.

## CLI

```powershell
uv run rld pc-living-dex "D:\path\to\POKEMON W.sav" --game white --scope regional --target-policy game-regional
```

Count party as owned, default:

```powershell
uv run rld pc-living-dex "D:\path\to\POKEMON W.sav" --game white --include-party
```

Ignore party and count PC only:

```powershell
uv run rld pc-living-dex "D:\path\to\POKEMON W.sav" --game white --no-include-party
```

## Scope

Currently supported:

```text
regional
```

Planned toggle:

```text
national
```

National mode is intentionally pending. Default stays regional Unova.

## Target policy

```text
game-regional   version-aware Unova PC Living Dex
all-regional    every BW Unova dex entry, including version/event/trade targets
catchable-only  direct in-game targets for the selected version
```

## Website vs executable

The local website is the first graphical interface because any computer with Python, an emulator, and a save file can use it. A packaged desktop `.exe` can be added later as a wrapper around the same local server.
