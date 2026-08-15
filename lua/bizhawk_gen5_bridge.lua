-- BizHawk Gen 5 bridge scaffold with a tiny JSON-over-TCP loop.
--
-- Load this in BizHawk while running a Gen 5 DS game with the melonDS core.
-- This is still a scaffold: Pokemon-specific memory addresses are not wired yet.

local BRIDGE_VERSION = "0.2.0"
local HOST = "127.0.0.1"
local PORT = 8765

local function log(message)
    console.log("[gen5-bridge] " .. message)
end

local function json_escape(value)
    value = tostring(value)
    value = value:gsub('\\', '\\\\')
    value = value:gsub('"', '\\"')
    value = value:gsub('\n', '\\n')
    return value
end

local function json_object(fields)
    local parts = {}
    for key, value in pairs(fields) do
        local encoded
        if type(value) == "number" or type(value) == "boolean" then
            encoded = tostring(value)
        else
            encoded = '"' .. json_escape(value) .. '"'
        end
        table.insert(parts, '"' .. json_escape(key) .. '":' .. encoded)
    end
    return "{" .. table.concat(parts, ",") .. "}"
end

local function current_state_stub()
    return json_object({
        bridge_version = BRIDGE_VERSION,
        status = "scaffold",
        emulator = "BizHawk",
        core = "melonDS",
        note = "Memory domains and Pokemon-specific addresses are not wired yet"
    })
end

local function frame_advance(frames)
    frames = tonumber(frames) or 1
    for _ = 1, frames do
        emu.frameadvance()
    end
    return json_object({ ok = true, method = "frame_advance", frames = frames })
end

local function press_button(button, frames)
    frames = tonumber(frames) or 1
    for _ = 1, frames do
        local input = {}
        input[button] = true
        joypad.set(input)
        emu.frameadvance()
    end
    return json_object({ ok = true, method = "press", button = button, frames = frames })
end

local function press_sequence(buttons_csv, frames, gap_frames)
    frames = tonumber(frames) or 1
    gap_frames = tonumber(gap_frames) or 1
    local count = 0
    for button in string.gmatch(buttons_csv or "", "([^,]+)") do
        press_button(button, frames)
        frame_advance(gap_frames)
        count = count + 1
    end
    return json_object({ ok = true, method = "press_sequence", count = count })
end

local function pause_emulator()
    client.pause()
    return json_object({ ok = true, method = "pause" })
end

local function resume_emulator()
    client.unpause()
    return json_object({ ok = true, method = "resume" })
end

local function checkpoint_stub(method)
    return json_object({ ok = false, method = method, error = "checkpoint support pending" })
end

local function screenshot_stub()
    return json_object({ ok = false, method = "screenshot", error = "screenshot support pending" })
end

local function extract_string(payload, key, default)
    local pattern = '"' .. key .. '"%s*:%s*"([^"]+)"'
    return payload:match(pattern) or default
end

local function extract_number(payload, key, default)
    local pattern = '"' .. key .. '"%s*:%s*(%d+)'
    return tonumber(payload:match(pattern)) or default
end

local function handle_request(payload)
    local method = extract_string(payload, "method", "")
    if method == "get_state" then
        return current_state_stub()
    end
    if method == "press" then
        local button = extract_string(payload, "button", "A")
        local frames = extract_number(payload, "frames", 1)
        return press_button(button, frames)
    end
    if method == "press_sequence" then
        local buttons_csv = extract_string(payload, "buttons_csv", "")
        local frames = extract_number(payload, "frames", 1)
        local gap_frames = extract_number(payload, "gap_frames", 1)
        return press_sequence(buttons_csv, frames, gap_frames)
    end
    if method == "frame_advance" then
        return frame_advance(extract_number(payload, "frames", 1))
    end
    if method == "pause" then
        return pause_emulator()
    end
    if method == "resume" then
        return resume_emulator()
    end
    if method == "save_checkpoint" then
        return checkpoint_stub("save_checkpoint")
    end
    if method == "load_checkpoint" then
        return checkpoint_stub("load_checkpoint")
    end
    if method == "screenshot" then
        return screenshot_stub()
    end
    return json_object({ ok = false, error = "unknown method", method = method })
end

local has_socket, socket = pcall(require, "socket")
if not has_socket then
    log("LuaSocket not available. TCP bridge disabled; functions are loaded for manual use.")
    log("Try manual smoke call: press_button('A', 2)")
    return
end

local server, err = socket.bind(HOST, PORT)
if not server then
    log("failed to bind " .. HOST .. ":" .. PORT .. " - " .. tostring(err))
    return
end
server:settimeout(0)
log("listening on " .. HOST .. ":" .. PORT .. " bridge v" .. BRIDGE_VERSION)

while true do
    local client = server:accept()
    if client then
        client:settimeout(0.25)
        local payload = client:receive("*l")
        if payload then
            local response = handle_request(payload)
            client:send(response .. "\n")
        else
            client:send(json_object({ ok = false, error = "empty request" }) .. "\n")
        end
        client:close()
    end
    emu.frameadvance()
end
