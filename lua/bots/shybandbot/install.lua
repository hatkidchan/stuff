local com = require('component')
local inet = com.internet
local base_url = 'https://raw.githubusercontent.com/undefinedvalue0103/stuff/master/lua/bots/shybandbot/'

local files = {
    ["main.lua"] = base_url .. "main.lua",
    ["utils.lua"] = base_url .. "utils.lua",
    ["privileges.lua"] = base_url .. "privileges.lua",
    ["handlers.lua"] = base_url .. "handlers.lua",
}

local function download(url, name)
  fd = io.open(name, "w")
  rq = inet.request(url)
  io.stdout:write("Loading " .. name .. " ... ")
  while true do
    chunk = rq.read(math.huge)
    if chunk then
      fd:write(chunk)
    else
      break
    end
  end
  print('done')
  fd:close()
end

for name, url in pairs(files) do
  download(url, name)
end
