local ops = {}
local privs = {}

function privs.reload_privileges()
  local fd = io.open('ops.txt', 'r')
  ops = {}
  while true do
    local line = fd:readLine():match('[^\n]+')
    table.insert(ops, line)
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
end

function privs.add_admin(name)
  table.insert(ops, name)
end

function privs.is_priv(name)
  for i, obj in ipairs(ops) do
    if obj == name then return true end
  end
end

return privs
