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

local function extract_string(payload, key, default)
    local pattern = '"' .. key .. '"%s*:%s*"([^"]+)"'
    return payload:match(pattern) or default
end

local function extract_number(payload, key, default)
    local pattern = '"' .. key .. '"%s*:%s*(%d+)'
    return tonumber(payload:match(pattern)) or default
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

local function handle_request(payload)
    local method = extract_string(payload, "method", "")
    local request_id = extract_string(payload, "id", "")
    local response
    if method == "get_state" then
        response = current_state_stub()
    elseif method == "press" then
        local button = extract_string(payload, "button", "A")
        local frames = extract_number(payload, "frames", 1)
        response = press_button(button, frames)
    elseif method == "press_sequence" then
        local buttons_csv = extract_string(payload, "buttons_csv", "")
        local frames = extract_number(payload, "frames", 1)
        local gap_frames = extract_number(payload, "gap_frames", 1)
        response = press_sequence(buttons_csv, frames, gap_frames)
    elseif method == "frame_advance" then
        response = frame_advance(extract_number(payload, "frames", 1))
    elseif method == "pause" then
        response = pause_emulator()
    elseif method == "resume" then
        response = resume_emulator()
    elseif method == "save_checkpoint" then
        response = checkpoint_stub("save_checkpoint")
    elseif method == "load_checkpoint" then
        response = checkpoint_stub("load_checkpoint")
    elseif method == "screenshot" then
        response = screenshot_stub()
    else
        response = json_object({ ok = false, error = "unknown method", method = method })
    end
    if request_id ~= "" then
        response = response:gsub("^%{", '{"id":"' .. json_escape(request_id) .. '",', 1)
    end
    return response
end

local function run_native_comm_bridge()
    comm.socketServerSetTimeout(50)
    log("using BizHawk native comm socket bridge: " .. tostring(comm.socketServerGetInfo()))
    comm.socketServerSend(json_object({ event = "ready", bridge_version = BRIDGE_VERSION }) .. "\n")
    while true do
        local payload = comm.socketServerResponse()
        if payload and payload ~= "" then
            local response = handle_request(payload)
            comm.socketServerSend(response .. "\n")
        end
        emu.frameadvance()
    end
end

local function run_luasocket_bridge(socket)
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
end

local has_socket, socket = pcall(require, "socket")
if has_socket then
    run_luasocket_bridge(socket)
else
    log("LuaSocket not available; falling back to BizHawk native comm socket bridge.")
    run_native_comm_bridge()
end
