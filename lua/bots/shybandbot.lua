local com = require('component')
local pc = require("computer")
local gpu = com.gpu
local ev = require('event')
local dbg = com.debug
local uni = require("unicode")

THRESHOLD_TS = 1
DISABLE_THROTTLING = true
BOX_NAME = 'Bot'
MESSAGE_PREFIX = '%'
IGNORE_GL = true

local ops = {
  UndefinedValue = 1,
  Sahalinus = 1,
}

local cmap = {
  [31] = {0, 0xff0000},
  [32] = {0, 0x00ff00},
  [33] = {0, 0xffff00},
  [34] = {0, 0x0000ff},
  [35] = {0, 0xff00ff},
  [36] = {0, 0x00ffff},
  [37] = {0, 0xaaaaaa},
}
function l_p(text)
  local function next()
    ch = uni.sub(text, 0, 1)
    text = uni.sub(text, 2)
    return ch
  end
  while text ~= '' do
    ch = next()
    if ch == '\x1b' then
      if next() ~= '[' then error('fuck') end
      local val = ''
      while true do
        ch = next()
        if ch == 'm' then break end
        val = val .. ch
      end
      local num = tonumber(val)
      if cmap[num] ~= nil then
        if cmap[num][1] == 0 then gpu.setForeground(cmap[num][2]) end
        if cmap[num][1] == 1 then gpu.setBackground(cmap[num][2]) end
      else
        gpu.setBackground(0x0); gpu.setForeground(0xffffff)
      end
    else
      io.stdout:write(ch)
    end
  end
end

function ssplit (inputstr, sep)
        if sep == nil then
                sep = "%s"
        end
        local t={}
        for str in string.gmatch(inputstr, "([^"..sep.."]+)") do
                table.insert(t, str)
        end
        return t
end

local function is_priv(name)
  return ops[name] or dbg.getPlayer(name).getGameType() == 'creative'
end
local function resolve_player(s, q)
  if q == '@s' then return s, dbg.getPlayer(s)
  else
    for _, name in ipairs(dbg.getPlayers()) do
      start, s_end = name:find(q)
      if start ~= nil then
        return name, dbg.getPlayer(name)
      end
    end
  end
  return false, nil
end

local function resolve_coord(rel_to, x, y, z)
  local nx, ny, nz = rel_to.getPosition()
  local ofx = x:sub(0, 1) == "~" and (tonumber(x:sub(2)) or 0) or nil
  local ofy = y:sub(0, 1) == "~" and (tonumber(y:sub(2)) or 0) or nil
  local ofz = z:sub(0, 1) == "~" and (tonumber(z:sub(2)) or 0) or nil
  local dx, dy, dz = nx, ny, nz
  if ofx ~= nil then dx = nx + ofx else dx = tonumber(x) or nx end
  if ofy ~= nil then dy = ny + ofy else dy = tonumber(y) or ny end
  if ofz ~= nil then dz = nz + ofz else dz = tonumber(z) or nz end
  return dx, dy, dz
end

local function handle_command(addr, sender, cmd, params)
  if cmd == 'help' then
    return {
      '~help - show this help',
      '~list - list players',
      '~say [something] - repeat message',
      '~info - show important info',
    }
  elseif cmd == 'say' then
    return table.concat(params, ' ')
  elseif cmd == 'list' then
    local players = dbg.getPlayers()
    local result = {'Players on server (' .. players.n .. '): '}
    for _, name in ipairs(players) do
      local p = dbg.getPlayer(name)
      local dimname = p.getWorld().getDimensionName()
      local x, y, z = p.getPosition()
      x, y, z = math.floor(x), math.floor(y), math.floor(z)
      local pos = x .. ', ' .. y .. ', ' .. z
      table.insert(result, name .. ' in ' .. dimname .. ' at ' .. pos)
    end
    return result
  elseif cmd == 'dist' then
    local me = dbg.getPlayer(sender)
    local my_world = me.getWorld()
    local mx, my, mz = me.getPosition()
    local result = {}
    for _, name in ipairs(dbg.getPlayers()) do
      local other = dbg.getPlayer(name)
      local o_world = other.getWorld()
      if o_world.getDimensionName() ~= my_world.getDimensionName() then
        table.insert(result, name .. ' in other dimension (' .. o_world.getDimensionName() .. ')!')
      elseif name == sender then
        table.insert(result, name .. ' <- it is you!')
      else
        local ox, oy, oz = other.getPosition()
        local dx, dy, dz = mx - ox, oy - my, mz - oz
        local dist3d = math.sqrt(math.pow(dx, 2) + math.pow(dy, 2) + math.pow(dz, 2))
        local dist2d = math.sqrt(math.pow(dx, 2) + math.pow(dz, 2))
        local rdist3d = math.floor(dist3d * 10) / 10
        local rdist2d = math.floor(dist2d * 10) / 10
        local rdy = math.floor(dy * 10) / 10
        table.insert(result, name .. ': ' .. rdist3d .. ' (' .. rdist2d .. 'h ' .. rdy .. 'v)')
      end
    end
    return result
  elseif cmd == 'give' then
    if not is_priv(sender) then return "Not allowed" end
    local user = table.remove(params, 1)
    local item = table.remove(params, 1) or 'stone'
    local count = tonumber(table.remove(params, 1) or 1)
    local meta = tonumber(table.remove(params, 1) or 0)
    local name, user_o = resolve_player(sender, user)
    user_o.insertItem(item, count, meta, '')
    return 'Given ' .. count .. ' of ' .. item .. '%' .. meta .. ' to ' .. user
  elseif cmd == 'tp' then
    if not is_priv(sender) then return "Not allowed" end
    local name_me, me = resolve_player(sender, '@s')
    if #params == 1 then
      local name, other = resolve_player(params[1], params[1])
      if name then
        me.setPosition(other.getPosition())
        return 'Teleported ' .. sender .. ' to ' .. name
      else
        return 'No such player'
      end
    elseif #params == 2 then
      local name1, from = resolve_player(sender, params[1])
      local name2, to = resolve_player(sender, params[2])
      if not name1 then return 'Target player not found' end
      if not name2 then return 'Destination player not found' end
      from.setPosition(to.getPosition())
      return 'Teleported ' .. name1 .. ' to ' .. name2
    elseif #params == 3 then
      local x, y, z = resolve_coord(me, params[1], params[2], params[3])
      me.setPosition(x, y, z)
      return 'Teleported ' .. sender .. ' to ' .. x .. ' ' .. y .. ' ' .. z
    elseif #params == 4 then
      local name, user = resolve_player(sender, params[1])
      if not name then return 'No such user' end
      local x, y, z = resolve_coord(user, params[2], params[3], params[4])
      user.setPosition(x, y, z)
      return 'Teleported ' .. name .. ' to ' .. x .. ' ' .. y .. ' ' .. z
    end
  elseif cmd == 'led' then
    local color = tonumber(params[1] or "", 16) or math.random(0, 0xfff)
    local r = bit32.band(bit32.rshift(color, 8), 15)
    local g = bit32.band(bit32.rshift(color, 4), 15)
    local b = bit32.band(color, 15)
    -- print(r, g, b)
    rgb = 0
    rgb = bit32.bor(rgb, bit32.lshift(r, 11))
    rgb = bit32.bor(rgb, bit32.lshift(g, 6))
    rgb = bit32.bor(rgb, bit32.lshift(b, 2))
    com.modem.broadcast(1234, 'setled', rgb)
    return 'Changing color to ' .. rgb
  elseif cmd == 'fill' then
    if not is_priv(sender) then return end
    local me = dbg.getPlayer(sender)
    local x, y, z = me.getPosition()
    x, y, z = math.floor(x), math.floor(y), math.floor(z)
    local blk = params[1] or 'grass'
    me.getWorld().setBlocks(x - 2, y - 1, z - 2, x + 2, y - 1, z + 2, blk, 0, '')
  else
    -- invalid command
    return nil
  end
end
local function handle_message(addr, sender, text)
  if text == 'ayy' then
    return 'lmao'
  elseif text == 'f' then
    return {
      'FFFFFFFF',
      'FF      ',
      'FFFFFFFF',
      'FF      ',
      'FF      ',
      'FF      ',
    }
  end
end
local function handle_event(etype, addr, params)
  if etype == 'component_added' then
    l_p('\x1b[31m[COM] \x1b[32m+ ' .. addr .. '\x1b[33m -> \x1b[34m' .. params[1] .. '\n')
    pc.beep(2000, 0.1)
    pc.beep(2000, 0.1)
  elseif etype == 'component_removed' then
    l_p('\x1b[31m[COM] \x1b[31m- ' .. addr .. '\x1b[33m -> \x1b[34m' .. params[1] .. '\n')
    pc.beep(2000, 0.1)
    pc.beep(1000, 0.1)
  end
end

local function handle_chat_message(addr, sender, message)
  local box = com.proxy(addr)
  l_p('\x1b[31m[MSG] \x1b[35m' .. addr:sub(0, 8) .. '\x1b[33m%\x1b[32m' .. sender .. '\x1b[33m: \x1b[34m' .. message .. '\n')
  local result
  if message:sub(0, 1) == MESSAGE_PREFIX then
    local params = ssplit(message:sub(2), ' ')
    local command = table.remove(params, 1)
    params_s = table.concat(params, ' ')
    l_p('\x1b[31m[CMD] \x1b[35m' .. addr:sub(0, 8) .. '\x1b[33m%\x1b[32m' .. sender .. '\x1b[33m: \x1b[35m' .. command .. ' \x1b[34m' .. params_s .. '\n')
    succ, result = pcall(handle_command, addr, sender, command, params)
    if not succ then
      l_p('\x1b[31m[ERR] \x1b[33m' .. tostring(result) .. '\n')
      box.setName('ERROR')
      box.say(tostring(result), math.huge)
      return
    end
  else
    succ, result = pcall(handle_message, addr, sender, message)
    if not succ then
      l_p('\x1b[31m[ERR] \x1b[33m' .. tostring(result) .. '\n')
      return
    end
  end
  box.setName(BOX_NAME)
  if result == nil then
    return
  elseif type(result) == 'table' then
    for _, v in ipairs(result) do
      l_p("\x1b[31m[REP] \x1b[35m" .. addr:sub(0, 8) .. " \x1b[33m-> \x1b[35m" .. v .. "\n")
      box.say(v, math.huge)
    end
  else
    local result = tostring(result)
    l_p("\x1b[31m[REP] \x1b[35m" .. addr:sub(0, 8) .. " \x1b[33m-> \x1b[35m" .. result .. "\n")
    box.say(result, math.huge)
  end
end

pc.beep(2000, 0.1)
l_p('\x1b[31m[INF] \x1b[32mBot init OK\n')
local runtime = 0
local last_message_ts = 0
while true do
  local e = table.pack(ev.pull())
  etype = table.remove(e, 1)
  addr = table.remove(e, 1)
  if etype == 'interrupted' then
    break
  elseif etype == 'chat_message' then
    sender = table.remove(e, 1)
    message = table.remove(e, 1)
    if IGNORE_GL and message:sub(0, 1) == '!' then message = message:sub(2) end
    local now = pc.uptime()
    if now - last_message_ts > (THRESHOLD_TS + runtime) or DISABLE_THROTTLING then
      start = pc.uptime()
      handle_chat_message(addr, sender, message)
      runtime = pc.uptime() - start
      last_message_ts = now
    end
  else
    local succ, result = pcall(handle_event, etype, addr, e)
    if not succ then
      l_p('\x1b[31m[ERR] \x1b[33m' .. tostring(result) .. '\n')
    end
  end
end
pc.beep(1000, 0.1)
l_p('\x1b[31m[INF] \x1b[33mBot stopped\n')