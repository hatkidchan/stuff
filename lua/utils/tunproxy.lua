local com = require('component')
local term = require('term')
local event = require('event')
local computer = require('computer')
local unicode = require('unicode')
local repr = require('serialization').serialize

local gpu = com.getPrimary('gpu')
local tunnel = com.getPrimary('tunnel')
local modem = com.getPrimary('modem')

DEFAULT_PORTS = {
  1234, 1111, 9050, 8080, 80, 22, 8022
}

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

local function printf(format, ...)
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

local packets = {net=0, tun=0}
local sw, sh = gpu.getResolution()
local start = computer.uptime()

for i, port in ipairs(DEFAULT_PORTS) do
  modem.open(port)
  printf('\x1b[31m[ INF ]\x1b[32m Opened port \x1b[34m%d\n', port)
end

while true do
  local up = math.floor(computer.uptime() - start)
  local m = math.floor(up / 60)
  local s = up - m * 60
  local h = math.floor(m / 60)
  m = m - h * 60
  gpu.setBackground(0xffffff)
  gpu.setForeground(0x000000)
  gpu.fill(1, 1, sw, 1, " ")
  gpu.set(1, 1, string.format("net: %05d tun: %05d | up: %05d:%2d:%2d", packets.net, packets.tun, h, m, s))
  gpu.setBackground(0x000000)
  term.setCursor(1, sh)
  local e = table.pack(event.pull(1))
  local etype = table.remove(e, 1)
  local addr = table.remove(e, 1)
  if etype == 'interrupted' then
    break
  elseif etype == nil then
    -- no event
  elseif etype == 'modem_message' then
    local sender = table.remove(e, 1)
    local port = table.remove(e, 1)
    local distance = table.remove(e, 1)
    local is_tun = addr == tunnel.address
    printf('\x1b[33m===> \x1b[35mTUN \x1b[34m%s \x1b[35mNET \x1b[33m<===\n', is_tun and '=>' or '<=')
    if is_tun then
      packets.tun = packets.tun + 1
      port = table.remove(e, 1)
      modem.open(port)
      modem.broadcast(port, table.unpack(e))
    else
      packets.net = packets.net + 1
      tunnel.send(port, table.unpack(e))
    end
    printf('\x1b[35m> sender: \x1b[34m%s\x1b[33m:\x1b[36m%d\n', sender, port)
    for i, item in ipairs(e) do
      printf('\x1b[35m[\x1b[34m%d\x1b[35m]> \x1b[36m%s\n', i, repr(item))
    end
    printf('\x1b[33m===> \x1b[31mEND OF MSG \x1b[33m<===\n')
  end
end
printf('\x1b[31m[FATAL] \x1b[91mExiting...\n')
computer.beep(1000, 0.1)

