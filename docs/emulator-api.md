# Emulator API

The dashboard and future agents control BizHawk through a local Python REST API, which talks to the Lua bridge over localhost TCP.

## Lua bridge

Load:

```text
lua/bizhawk_gen5_bridge.lua
```

Expected default endpoint:

```text
127.0.0.1:8765
```

## REST endpoints

```text
POST /api/emulator/launch
GET  /api/emulator/state
POST /api/emulator/press
POST /api/emulator/press-sequence
POST /api/emulator/frame-advance
POST /api/emulator/pause
POST /api/emulator/resume
POST /api/emulator/checkpoint/save
POST /api/emulator/checkpoint/load
GET  /api/emulator/screenshot
```

Examples:

```json
POST /api/emulator/launch
{}
```

This launches BizHawk with the configured Pokemon White ROM. It does not yet auto-run the Lua bridge; load the Lua bridge from BizHawk's Lua Console if it is not already running.

```json
POST /api/emulator/press
{
  "button": "A",
  "frames": 2
}
```

```json
POST /api/emulator/press-sequence
{
  "buttons": ["A", "B", "Start"],
  "frames": 1,
  "gap_frames": 1
}
```

```json
POST /api/emulator/frame-advance
{
  "frames": 30
}
```

Checkpoint and screenshot support are protocol-shaped but still scaffolded in Lua.

## Telemetry

```text
GET /api/telemetry
WS  /ws/telemetry
```

Telemetry is currently in-memory and intended for the dashboard/debug loop. Supabase persistence can be added later.

## Principle

Do not expose raw memory tools as the normal agent interface. Keep raw debugger capabilities separate from semantic Pokemon tools.
