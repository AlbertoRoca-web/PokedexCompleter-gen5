-- BizHawk Gen 5 bridge scaffold with a tiny JSON-over-TCP loop.
--
-- Load this in BizHawk while running a Gen 5 DS game with the melonDS core.
-- This is still a scaffold: Pokemon-specific memory addresses are not wired yet.

local BRIDGE_VERSION = "0.3.0"
local HOST = "127.0.0.1"
local PORT = 8765
local DEFAULT_SPEED_PERCENT = 400

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

local function set_emulator_speed(percent)
    percent = tonumber(percent) or DEFAULT_SPEED_PERCENT
    local ok, result = pcall(function()
        client.speedmode(percent)
        return true
    end)
    if not ok then
        return json_object({ ok = false, method = "emulator.set_speed", percent = percent, error = tostring(result) })
    end
    return json_object({ ok = result == true, method = "emulator.set_speed", percent = percent })
end

local function bridge_info()
    local frame_count = 0
    local approx_framerate = 0
    local turbo = false
    pcall(function()
        frame_count = emu.framecount()
    end)
    pcall(function()
        approx_framerate = client.get_approx_framerate()
    end)
    pcall(function()
        turbo = client.isturbo()
    end)
    return json_object({
        ok = true,
        method = "bridge.info",
        bridge_version = BRIDGE_VERSION,
        emulator = "BizHawk",
        core = "melonDS",
        frame_count = frame_count,
        approx_framerate = approx_framerate,
        turbo = turbo,
        configured_speed_percent = DEFAULT_SPEED_PERCENT
    })
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

local function touch_screen(x, y, frames)
    x = math.max(0, math.min(255, tonumber(x) or 0))
    y = math.max(0, math.min(255, tonumber(y) or 0))
    frames = math.max(1, tonumber(frames) or 1)
    for _ = 1, frames do
        joypad.set({ ["Touch X"] = x, ["Touch Y"] = y, ["Touch"] = true })
        emu.frameadvance()
    end
    joypad.set({})
    return json_object({ ok = true, method = "touch", x = x, y = y, frames = frames })
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

local function save_checkpoint(path)
    if path == nil or path == "" then
        return json_object({ ok = false, method = "save_checkpoint", error = "path is required" })
    end
    local ok, result = pcall(function()
        return savestate.save(path, true)
    end)
    if not ok then
        return json_object({ ok = false, method = "save_checkpoint", path = path, error = tostring(result) })
    end
    return json_object({ ok = result == true, method = "save_checkpoint", path = path })
end

local function load_checkpoint(path)
    if path == nil or path == "" then
        return json_object({ ok = false, method = "load_checkpoint", error = "path is required" })
    end
    local ok, result = pcall(function()
        return savestate.load(path, true)
    end)
    if not ok then
        return json_object({ ok = false, method = "load_checkpoint", path = path, error = tostring(result) })
    end
    return json_object({ ok = result == true, method = "load_checkpoint", path = path })
end

local function screenshot(path)
    if path == nil or path == "" then
        return json_object({ ok = false, method = "screenshot", error = "path is required" })
    end
    local ok, result = pcall(function()
        client.screenshot(path)
        return true
    end)
    if not ok then
        return json_object({ ok = false, method = "screenshot", path = path, error = tostring(result) })
    end
    return json_object({ ok = result == true, method = "screenshot", path = path })
end

local function with_memory_domain(domain, callback)
    if domain ~= nil and domain ~= "" then
        memory.usememorydomain(domain)
    end
    return callback()
end

local function read_memory_u8(domain, address)
    address = tonumber(address) or 0
    local ok, result = pcall(function()
        return with_memory_domain(domain, function()
            return memory.read_u8(address)
        end)
    end)
    if not ok then
        return json_object({ ok = false, method = "memory.read_u8", domain = domain, address = address, error = tostring(result) })
    end
    return json_object({ ok = true, method = "memory.read_u8", domain = domain, address = address, value = result })
end

local function read_memory_bytes(domain, address, length)
    address = tonumber(address) or 0
    length = tonumber(length) or 1
    if length < 1 then
        length = 1
    end
    if length > 65536 then
        length = 65536
    end
    local ok, result = pcall(function()
        return with_memory_domain(domain, function()
            local values = {}
            local hex_values = {}
            for index = 0, length - 1 do
                local value = memory.read_u8(address + index)
                table.insert(values, tostring(value))
                table.insert(hex_values, string.format("%02X", value))
            end
            return table.concat(values, ",") .. "|" .. table.concat(hex_values, "")
        end)
    end)
    if not ok then
        return json_object({ ok = false, method = "memory.read_bytes", domain = domain, address = address, length = length, error = tostring(result) })
    end
    local values_csv, hex = result:match("([^|]*)|(.*)")
    return json_object({
        ok = true,
        method = "memory.read_bytes",
        domain = domain,
        address = address,
        length = length,
        values_csv = values_csv or "",
        hex = hex or ""
    })
end

local function diff_memory_after_press(domain, address, length, button, press_frames, advance_frames, max_changes)
    address = tonumber(address) or 0
    length = tonumber(length) or 1
    press_frames = tonumber(press_frames) or 5
    advance_frames = tonumber(advance_frames) or 120
    max_changes = tonumber(max_changes) or 500
    if length < 1 then
        length = 1
    end
    if length > 262144 then
        length = 262144
    end
    if max_changes < 1 then
        max_changes = 1
    end
    if max_changes > 2000 then
        max_changes = 2000
    end
    local ok, result = pcall(function()
        return with_memory_domain(domain, function()
            local before = {}
            for index = 0, length - 1 do
                before[index + 1] = memory.read_u8(address + index)
            end
            if button ~= nil and button ~= "" then
                press_button(button, press_frames)
            end
            frame_advance(advance_frames)
            local changes = {}
            local count = 0
            for index = 0, length - 1 do
                local after = memory.read_u8(address + index)
                local previous = before[index + 1]
                if previous ~= after then
                    count = count + 1
                    if #changes < max_changes then
                        table.insert(changes, string.format("%X:%d:%d", address + index, previous, after))
                    end
                end
            end
            return tostring(count) .. "|" .. table.concat(changes, ",")
        end)
    end)
    if not ok then
        return json_object({ ok = false, method = "memory.diff_after_press", domain = domain, address = address, length = length, error = tostring(result) })
    end
    local count_text, changes_csv = result:match("([^|]*)|(.*)")
    return json_object({
        ok = true,
        method = "memory.diff_after_press",
        domain = domain,
        address = address,
        length = length,
        button = button or "",
        press_frames = press_frames,
        advance_frames = advance_frames,
        changed_count = tonumber(count_text) or 0,
        changes_csv = changes_csv or ""
    })
end

local function list_memory_domains()
    local ok, result = pcall(function()
        local domains = memory.getmemorydomainlist()
        local names = {}
        for _, domain in ipairs(domains) do
            table.insert(names, domain)
        end
        return table.concat(names, ",")
    end)
    if not ok then
        return json_object({ ok = false, method = "memory.list_domains", error = tostring(result) })
    end
    local current = ""
    local size = 0
    pcall(function()
        current = memory.getcurrentmemorydomain()
        size = memory.getcurrentmemorydomainsize()
    end)
    return json_object({ ok = true, method = "memory.list_domains", domains_csv = result, current = current, current_size = size })
end

local function handle_request(payload)
    local method = extract_string(payload, "method", "")
    local request_id = extract_string(payload, "id", "")
    local response
    if method == "bridge.info" then
        response = bridge_info()
    elseif method == "emulator.set_speed" then
        response = set_emulator_speed(extract_number(payload, "percent", DEFAULT_SPEED_PERCENT))
    elseif method == "get_state" then
        response = current_state_stub()
    elseif method == "press" then
        local button = extract_string(payload, "button", "A")
        local frames = extract_number(payload, "frames", 1)
        response = press_button(button, frames)
    elseif method == "touch" then
        response = touch_screen(
            extract_number(payload, "x", 0),
            extract_number(payload, "y", 0),
            extract_number(payload, "frames", 1)
        )
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
        response = save_checkpoint(extract_string(payload, "path", ""))
    elseif method == "load_checkpoint" then
        response = load_checkpoint(extract_string(payload, "path", ""))
    elseif method == "screenshot" then
        response = screenshot(extract_string(payload, "path", ""))
    elseif method == "memory.list_domains" then
        response = list_memory_domains()
    elseif method == "memory.read_u8" then
        response = read_memory_u8(extract_string(payload, "domain", ""), extract_number(payload, "address", 0))
    elseif method == "memory.read_bytes" then
        response = read_memory_bytes(
            extract_string(payload, "domain", ""),
            extract_number(payload, "address", 0),
            extract_number(payload, "length", 1)
        )
    elseif method == "memory.diff_after_press" then
        response = diff_memory_after_press(
            extract_string(payload, "domain", ""),
            extract_number(payload, "address", 0),
            extract_number(payload, "length", 1),
            extract_string(payload, "button", ""),
            extract_number(payload, "press_frames", 5),
            extract_number(payload, "advance_frames", 120),
            extract_number(payload, "max_changes", 500)
        )
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
    set_emulator_speed(DEFAULT_SPEED_PERCENT)
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
    set_emulator_speed(DEFAULT_SPEED_PERCENT)
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
