-- Lua 5.4 checks for ark/Mods/GtaArkLink/Scripts/gal_link.lua (UE4SS runs plain Lua 5.4).
-- Run from mods/gta-ark: lua5.4 tests/test_gal_link.lua; also run by the confined lua profile.
package.path = "ark/Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local link = require("gal_link")
local failures = 0
local function check(cond, what)
  if not cond then failures = failures + 1; print("FAIL " .. what) end
end
local function near(a, b) return math.abs(a - b) < 1e-4 end

-- The C++ writer's sample (gta/build/cpp_sample.bin): same values as gal_record_test.cpp.
local fixture = assert(io.open("tests/gal1_fixture.hex", "r"))
local raw = fixture:read("a"):gsub("%s", ""):gsub("..", function(x) return string.char(tonumber(x, 16)) end)
fixture:close()
local r = link.unpack(raw)
check(r ~= nil, "shared GAL1 fixture is accepted")
if r then
  check(r.cam_pos[3] == 3 and r.cam_rot[3] == 45 and r.fov == 50, "camera fields")
  check(r.heading == 90 and r.flags == 3 and r.frame == 7, "player, flags, frame")
end
check(link.unpack(("x"):rep(63)) == nil, "short record rejected")
for offset = 8, 48, 4 do
  for _, value in ipairs({0/0, math.huge, -math.huge}) do
    local changed = raw:sub(1, offset) .. string.pack("<f", value) .. raw:sub(offset + 5)
    check(link.unpack(changed) == nil, "invalid float rejected at " .. offset)
  end
end
for _, value in ipairs({0, -1, 180, 1000}) do
  local changed = raw:sub(1, 32) .. string.pack("<f", value) .. raw:sub(37)
  check(link.unpack(changed) == nil, "invalid FOV rejected")
end

-- Same cases as tests/vectors.json.
local go, gy, uo, uy = {100, 200, 30}, 0, {5000, -3000, 1200}, 90
local cases = {
  {{100, 201, 30}, {0, 0, 0}, {5100, -3000, 1200}, {0, 90, 0}},
  {{101, 200, 30}, {0, 0, 0}, {5000, -2900, 1200}, {0, 90, 0}},
  {{100, 200, 30}, {0, 0, 90}, {5000, -3000, 1200}, {0, 0, 0}},
  {{100, 200, 30}, {0, 10, 0}, {5000, -3000, 1200}, {0, 90, -10}},
  {{100, 200, 30}, {0, 0, -100}, {5000, -3000, 1200}, {0, -170, 0}},
}
for i, c in ipairs(cases) do
  local loc, rot = link.to_unreal(c[1], c[2], go, gy, uo, uy)
  for k = 1, 3 do
    check(near(loc[k], c[3][k]) and near(rot[k], c[4][k]), "transform case " .. i)
  end
end

local t = link.new_tracker(2)
check(link.observe(t, {sequence = 2}) == false, "fresh record is not stale")
link.observe(t, {sequence = 2}); link.observe(t, {sequence = 2})
check(link.observe(t, {sequence = 2}) == true, "unchanged sequence goes stale")

print(failures == 0 and "test_gal_link.lua: OK" or ("test_gal_link.lua: " .. failures .. " failure(s)"))
os.exit(failures == 0 and 0 or 1)
