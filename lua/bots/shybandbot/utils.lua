local utils = {}
local unicode = require('unicode')
local com = require('component')
local json = require('json')
local gpu = com.gpu
local dbg = com.debug

local cmap = {
  [31] = {0, 0xff0000},
  [32] = {0, 0x00ff00},
  [33] = {0, 0xffff00},
  [34] = {0, 0x0000ff},
  [35] = {0, 0xff00ff},
  [36] = {0, 0x00ffff},
  [37] = {0, 0x787878},

  [91] = {0, 0xff7878},
  [92] = {0, 0x78ff78},
  [93] = {0, 0xffff78},
  [94] = {0, 0x7878ff},
  [95] = {0, 0xff78ff},
  [96] = {0, 0x78ffff},
  [97] = {0, 0xaaaaaa},
}

function utils.printf(format, ...)
  local text = string.format(format, ...)
  local function next()
    ch = unicode.sub(text, 0, 1)
    text = unicode.sub(text, 2)
    return ch
  end
  while text ~= '' do
    ch = next()
    if ch == '\x1b' then
      if next() ~= '[' then error('peck') end
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


function utils.resolve_coord(rel_to, x, y, z)
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

function utils.resolve_player(s, q)
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

function utils.ssplit(inputstr, sep)
  if sep == nil then sep = "%s" end
  local t = {}
  for str in string.gmatch(inputstr, "([^"..sep.."]+)") do
    table.insert(t, str)
  end
  return t
end

function utils.traceback(err)
  utils.printf('\x1b[31m[ERR] \x1b[33m%s\n', err or 'Stack trace:')
  for i, line in ipairs(utils.ssplit(debug.traceback(), '\n')) do
    utils.printf('\x1b[31m[ERR] \x1b[33m%d: \x1b[31m%s\n', i, line)
  end
end

function utils.chat_trace(err)
  local cb = require('component').getPrimary('chat_box')
  cb.setName('ERROR')
  cb.say(err or 'Stack trace:')
  for i, line in ipairs(utils.ssplit(debug.traceback(), '\n')) do
    cb.say(line, math.huge)
  end
end

function utils.init_box(addr)
  local cbox = com.proxy(addr)
  cbox.setName(BOX_NAME)
  local dist = cbox.setDistance(math.huge)
  utils.printf('\x1b[31m[INF] \x1b[32mBox \x1b[35m%s\x1b[32m initialized with name \x1b[34m%s \x1b[32mand distance \x1b[33m%d\n', addr:sub(0, 8), BOX_NAME, dist)
end

-- https://github.com/daurnimator/lua-http/blob/master/http/util.lua
-- with little modifications
local function char_to_pchar(c)
  return string.format('%%%02X', c:byte(1,1))
end

local function encodeURIComponent(str)
  return (str:gsub('[^%w%-_%.%!%~%*%\'%(%)]', char_to_pchar))
end

local function dict_to_query(form)
  local r = {}
  for name, value in pairs(form) do
    table.insert(r, encodeURIComponent(name)..'='..encodeURIComponent(value))
  end
  return table.concat(r, '&')
end

function utils.http_get(addr, params, headers)
  local handle, err = com.getPrimary('internet').request(addr .. '?' .. dict_to_query(params or {}), nil, headers)
  if not handle then return nil, err end -- failed to open connection
  local code, message, headers = handle.response()
  local response = ''
  while true do
    local chunk = handle.read(math.huge)
    if not chunk then break end
    response = response .. chunk
  end
  return response, code, message, headers
end

function utils.json_get(addr, params, headers)
  local response, code, message, headers = utils.http_get(addr, params)
  if not response then return nil, code end
  return json:decode(response), code, message, headers
end

return utils
