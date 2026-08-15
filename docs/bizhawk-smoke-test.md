# BizHawk Bridge Smoke Test

This is a manual test for Alberto's machine once BizHawk + melonDS is installed and Pokémon Gen 5 is running.

## Preconditions

- BizHawk installed.
- Nintendo DS melonDS core available in BizHawk.
- A legally obtained Gen 5 game is loaded.
- `lua/bizhawk_gen5_bridge.lua` is loaded through BizHawk's Lua console.
- LuaSocket is available in the BizHawk Lua environment, or the bridge will log that TCP is disabled.

## Start bridge

In BizHawk:

```text
Tools -> Lua Console -> Open Script -> lua/bizhawk_gen5_bridge.lua
```

Expected log:

```text
[gen5-bridge] listening on 127.0.0.1:8765 bridge v0.1.0
```

If LuaSocket is missing, expected log:

```text
LuaSocket not available. TCP bridge disabled; functions are loaded for manual use.
```

## Python smoke

From repo root:

```powershell
uv run python -c "from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkClient; print(BizHawkClient().get_state())"
```

Expected response:

```python
{
  'bridge_version': '0.1.0',
  'status': 'scaffold',
  'emulator': 'BizHawk',
  'core': 'melonDS',
  'note': 'Memory domains and Pokemon-specific addresses are not wired yet'
}
```

Button smoke:

```powershell
uv run python -c "from pokedex_completer_gen5.emulator.bizhawk_client import BizHawkClient; print(BizHawkClient().press('A', 2))"
```

The game should receive A for two frames.

## Current limitations

- No Pokémon-specific memory addresses are wired yet.
- No structured map/party/battle state yet.
- JSON parser in Lua is intentionally tiny and only supports the current simple requests.
- This is a bridge smoke test, not the full agent loop.
