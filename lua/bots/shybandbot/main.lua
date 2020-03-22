local com = require('component')
local pc = require("computer")
local ev = require('event')
local utils = require('utils')
local handlers = require('handlers')

THRESHOLD_TS = 1
DISABLE_THROTTLING = true
BOX_NAME = 'Bot'
MESSAGE_PREFIX = '%'
IGNORE_GL = true

local function handle_event(etype, addr, params)
  if etype == 'component_added' then
    utils.printf('\x1b[31m[COM] \x1b[32m+ %s\x1b[33m -> \x1b[34m%s\n', addr, params[1])
    pc.beep(2000, 0.1)
    pc.beep(2000, 0.1)
  elseif etype == 'component_removed' then
    utils.printf('\x1b[31m[COM] \x1b[31m- %s\x1b[33m -> \x1b[34m%s\n', addr, params[1])
    pc.beep(2000, 0.1)
    pc.beep(1000, 0.1)
  end
end

local function handle_chat_message(addr, sender, message)
  local box = com.proxy(addr)
  utils.printf('\x1b[31m[MSG] \x1b[35m%s\x1b[33m%\x1b[32m%s\x1b[33m: \x1b[34m%s\n', addr:sub(0, 8), sender, message)
  local succ, result
  if message:sub(0, 1) == MESSAGE_PREFIX then
    local params = utils.ssplit(message:sub(2), ' ')
    local command = table.remove(params, 1)
    params_s = table.concat(params, ' ')
    utils.printf('\x1b[31m[CMD] \x1b[35m%s\x1b[33m%\x1b[32m%s\x1b[33m: \x1b[35m%s \x1b[34m%s\n', addr:sub(0, 8), sender, command, params_s)
    succ, result = pcall(handlers.command, addr, sender, command, params)
  else
    succ, result = pcall(handlers.message, addr, sender, message)
  end
  if not succ then
    box.setName('ERROR')
    box.say(tostring(result), math.huge)
    utils.printf('\x1b[31m[ERR] \x1b[33m%s\n', result)
    return
  end
  if not result then return end
  box.setName(BOX_NAME)
  if type(result) ~= 'table' then
    result = { tostring(result) }
  end
  for _, v in ipairs(result) do
    utils.printf('\x1b[31m[REP] \x1b[35m%s \x1b[33m-> \x1b[35m%s\n', addr:sub(0, 8), v)
    box.say(v, math.huge)
  end
end

pc.beep(2000, 0.1)
utils.printf('\x1b[31m[INF] \x1b[32mBot init OK\n')
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
    local succ, resp = pcall(handle_chat_message, addr, sender, message)  -- TODO: implement dublicates detection
    if not succ then
      box.setName('ERROR')
      box.say(tostring(resp), math.huge)
    end
  else
    local succ, result = pcall(handle_event, etype, addr, e)
    if not succ then
      l_p('\x1b[31m[ERR] \x1b[33m' .. tostring(result) .. '\n')
    end
  end
end
pc.beep(1000, 0.1)
utils.printf('\x1b[31m[INF] \x1b[33mBot stopped\n')

