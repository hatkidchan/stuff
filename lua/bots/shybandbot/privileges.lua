local ops = {}
local privs = {}

function privs.reload_privileges()
  local fd = io.open('ops.txt', 'r')
  ops = {}
  while true do
    local line = fd:readLine()
    if not line then break end
    table.insert(ops, line:match('[^\n]+'))
  end
  return ops
end

function privs.flush_privileges()
  local fd = io.open('ops.txt', 'w')
  for i, name in ipairs(ops) do
    fd:writeLine(name)
  end
  fd:close()
end

function privs.remove_admin(name)
  for i, obj in ipairs(ops) do
    if obj == name then table.remove(ops, i) end
  end
  privs.flush_privileges()
end

function privs.add_admin(name)
  table.insert(ops, name)
  privs.flush_privileges()
end

function privs.is_priv(name)
  for i, obj in ipairs(ops) do
    if obj == name then return true end
  end
end

privs.reload_privileges()

return privs
