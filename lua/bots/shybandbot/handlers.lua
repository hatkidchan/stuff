local utils = require('utils')
local privs = require('privileges')
local com = require('component')
local dbg = com.debug

local handlers = {}

function handlers.command(addr, sender, cmd, params)
  if cmd == 'help' then
    return {
      'help - show this help',
      'list - list players',
      'say [something] - repeat message',
      'info - show important info',
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
    if not privs.is_priv(sender) then return "Not allowed" end
    local user = table.remove(params, 1)
    local item = table.remove(params, 1) or 'stone'
    local count = tonumber(table.remove(params, 1) or 1)
    local meta = tonumber(table.remove(params, 1) or 0)
    local name, user_o = utils.resolve_player(sender, user)
    user_o.insertItem(item, count, meta, '')
    return 'Given ' .. count .. ' of ' .. item .. '%' .. meta .. ' to ' .. user
  elseif cmd == 'tp' then
    if not privs.is_priv(sender) then return "Not allowed" end
    local name_me, me = utils.resolve_player(sender, '@s')
    if #params == 1 then
      local name, other = utils.resolve_player(params[1], params[1])
      if name then
        me.setPosition(other.getPosition())
        return 'Teleported ' .. sender .. ' to ' .. name
      else
        return 'No such player'
      end
    elseif #params == 2 then
      local name1, from = utils.resolve_player(sender, params[1])
      local name2, to = utils.resolve_player(sender, params[2])
      if not name1 then return 'Target player not found' end
      if not name2 then return 'Destination player not found' end
      from.setPosition(to.getPosition())
      return 'Teleported ' .. name1 .. ' to ' .. name2
    elseif #params == 3 then
      local x, y, z = utils.resolve_coord(me, params[1], params[2], params[3])
      me.setPosition(x, y, z)
      return 'Teleported ' .. sender .. ' to ' .. x .. ' ' .. y .. ' ' .. z
    elseif #params == 4 then
      local name, user = utils.resolve_player(sender, params[1])
      if not name then return 'No such user' end
      local x, y, z = utils.resolve_coord(user, params[2], params[3], params[4])
      user.setPosition(x, y, z)
      return 'Teleported ' .. name .. ' to ' .. x .. ' ' .. y .. ' ' .. z
    end
  elseif cmd == 'led' then
    local color = tonumber(params[1] or "", 16) or math.random(0, 0xfff)
    local r = bit32.band(bit32.rshift(color, 8), 15)
    local g = bit32.band(bit32.rshift(color, 4), 15)
    local b = bit32.band(color, 15)
    rgb = 0
    rgb = bit32.bor(rgb, bit32.lshift(r, 11))
    rgb = bit32.bor(rgb, bit32.lshift(g, 6))
    rgb = bit32.bor(rgb, bit32.lshift(b, 2))
    com.modem.broadcast(1234, 'setled', rgb)
    return 'Changing color to ' .. rgb
  elseif cmd == 'fill' then
    if not privs.is_priv(sender) then return 'Not allowed' end
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

function handlers.message(addr, sender, text)
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

function handlers.event(etype, addr, params)

end

return handlers
