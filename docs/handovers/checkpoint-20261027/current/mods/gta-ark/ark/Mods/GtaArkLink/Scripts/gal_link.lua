-- GAL1 link reader and GTA -> Unreal transform for the ARK side (see link-format.md).
-- Pure Lua 5.4 (UE4SS runs plain Lua: no FFI, no high-resolution clock), so it can be tested
-- outside the game. Mirrors tools/gal_link.py and tests/vectors.json.
local M = {}

M.SIZE = 64
M.FLAG_STORY = 1
M.FLAG_ENABLED = 2
local FIELDS = "<c4I4fffffffffffI4I8"  -- 11 floats; exactly 64 bytes including magic, sequence, flags and frame
assert(string.packsize(FIELDS) == M.SIZE, "GAL1 record layout must be exactly 64 bytes")

function M.default_path()
  return (os.getenv("LOCALAPPDATA") or ".") .. "\\SMELTER\\gta-ark-link\\camera.bin"
end

-- Returns a record table for a complete record, or nil for torn, foreign or in-progress data.
function M.unpack(raw)
  if type(raw) ~= "string" or #raw ~= M.SIZE then return nil end
  local magic, seq, cx, cy, cz, pitch, roll, yaw, fov, px, py, pz, heading, flags, frame = string.unpack(FIELDS, raw)
  if magic ~= "GAL1" or seq % 2 == 1 then return nil end
  for _, value in ipairs({cx, cy, cz, pitch, roll, yaw, fov, px, py, pz, heading}) do
    if value ~= value or value == math.huge or value == -math.huge then return nil end
  end
  if fov <= 0 or fov >= 180 then return nil end
  return {sequence = seq, cam_pos = {cx, cy, cz}, cam_rot = {pitch, roll, yaw}, fov = fov,
          player_pos = {px, py, pz}, heading = heading, flags = flags, frame = frame}
end

-- Seqlock read: accept only when two consecutive reads of the file agree.
function M.read(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local first = f:read(M.SIZE)
  f:seek("set", 0)
  local second = f:read(M.SIZE)
  f:close()
  if first == nil or first ~= second then return nil end
  return M.unpack(first)
end

-- Staleness by ticks (Lua has no high-resolution clock): stale when the sequence has not
-- changed for `limit` consecutive ticks (about 1 s at the reader's tick rate).
function M.new_tracker(limit)
  return {limit = limit, last = nil, idle = math.huge}
end

function M.observe(tracker, record)
  if record and record.sequence ~= tracker.last then
    tracker.last, tracker.idle = record.sequence, 0
  else
    tracker.idle = tracker.idle + 1
  end
  return tracker.idle > tracker.limit  -- true = stale
end

-- GTA (metres, Z up, X east, Y north, yaw counter-clockwise) -> Unreal (cm, X forward,
-- Y right, yaw clockwise), relative to the positions and yaws captured at link start.
function M.to_unreal(gta_pos, gta_rot, gta_origin, gta_yaw_origin, ue_origin, ue_yaw_origin)
  local dx = gta_pos[1] - gta_origin[1]
  local dy = gta_pos[2] - gta_origin[2]
  local dz = gta_pos[3] - gta_origin[3]
  local location = {ue_origin[1] + 100 * dy, ue_origin[2] + 100 * dx, ue_origin[3] + 100 * dz}
  local pitch, roll, yaw = gta_rot[1], gta_rot[2], gta_rot[3]
  local ue_yaw = (ue_yaw_origin - (yaw - gta_yaw_origin) + 180) % 360 - 180
  return location, {pitch, ue_yaw, -roll}
end

return M
