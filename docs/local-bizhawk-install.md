# Local BizHawk Install

Installed by Izamatsu on Alberto's machine.

## Paths

BizHawk executable:

```text
D:\alroc\codepup\tools\BizHawk-2.11.1\EmuHawk.exe
```

Downloaded archive:

```text
D:\alroc\codepup\tools\BizHawk-2.11.1-win-x64.zip
```

Convenience launcher:

```text
tools\launch-bizhawk.cmd
```

Repo Lua bridge source:

```text
lua\bizhawk_gen5_bridge.lua
```

Copied convenience Lua bridge inside BizHawk:

```text
D:\alroc\codepup\tools\BizHawk-2.11.1\Lua\bizhawk_gen5_bridge.lua
```

## Load flow

1. Open BizHawk with `tools\launch-bizhawk.cmd` or directly run `EmuHawk.exe`.
2. `File -> Open ROM` and select Alberto's legally dumped Pokemon White `.nds`.
3. Verify the save loads.
4. `Tools -> Lua Console`.
5. Open script:

```text
D:\alroc\codepup\tools\BizHawk-2.11.1\Lua\bizhawk_gen5_bridge.lua
```

Expected bridge message:

```text
[gen5-bridge] listening on 127.0.0.1:8765 bridge v0.2.0
```

If LuaSocket is missing, the bridge will log that TCP is disabled. BizHawk 2.11.1 appears to include Lua socket/mime folders, so this should hopefully work.
