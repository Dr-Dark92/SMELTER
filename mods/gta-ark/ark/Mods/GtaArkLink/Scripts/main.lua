-- Prototype engine bindings; real ARK/UE4SS compatibility is still unverified.
-- Only a local standalone player with a valid camera and pawn can follow GAL1.
local link = require("gal_link")
local PATH, TICK_MS = link.default_path(), 33
local tracker = link.new_tracker(30)
local origin, identity, state = nil, nil, nil

local function valid(object)
  return object and object:IsValid()
end

local function say(text, pc)
  if state == text then return end
  state = text
  print("[GtaArkLink] " .. text .. "\n")
  if pc then pcall(function() pc:ClientMessage("GTA link: " .. text) end) end
end

local function reset()
  origin, identity = nil, nil
end

local function controller()
  for _, pc in ipairs(FindAllOf("PlayerController") or {}) do
    if valid(pc) and pc:IsLocalPlayerController() then return pc end
  end
end

local function tick()
  local pc = controller()
  if not pc then reset(); say("waiting for local player"); return end
  local system = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
  if not valid(system) then reset(); say("waiting for standalone check"); return end
  -- A failed/unknown reflected standalone check stops this tick.
  if not system:IsStandalone(pc) then reset(); say("standalone session required"); return end
  local pawn, camera = pc.Pawn, pc.PlayerCameraManager
  if not valid(pawn) or not valid(camera) then
    reset(); say("waiting for pawn and camera"); return
  end
  local current = tostring(pc:GetAddress()) .. ":" .. tostring(pawn:GetAddress())
  if identity ~= current then
    local changed = identity ~= nil
    reset(); identity = current; tracker = link.new_tracker(30)
    if changed then state = nil end
  end
  local record = link.read(PATH)
  local stale = link.observe(tracker, record)
  local required = link.FLAG_STORY | link.FLAG_ENABLED
  if stale or not record or record.flags & required ~= required then
    origin = nil
    say(record and not stale and "waiting for GTA Story Mode link" or
        (tracker.last and "stale" or "waiting"), pc)
    return
  end
  if not origin then
    -- Anchor the pawn to its own location, not its offset camera/eye position.
    local position, rotation = pawn:K2_GetActorLocation(), camera:GetCameraRotation()
    origin = {gta = record.cam_pos, gta_yaw = record.cam_rot[3],
              ue = {position.X, position.Y, position.Z}, ue_yaw = rotation.Yaw}
  end
  local location, rotation = link.to_unreal(record.cam_pos, record.cam_rot,
    origin.gta, origin.gta_yaw, origin.ue, origin.ue_yaw)
  local moved = pawn:K2_SetActorLocation(
    {X = location[1], Y = location[2], Z = location[3]}, false, {}, true)
  if moved ~= true then origin = nil; say("pawn movement unavailable", pc); return end
  pc:SetControlRotation({Pitch = rotation[1], Yaw = rotation[2], Roll = rotation[3]})
  say("following", pc)
end

if type(LoopInGameThreadWithDelay) ~= "function" then
  say("blocked: UE4SS game-thread timer API is unavailable")
  return
end
local started, err = pcall(LoopInGameThreadWithDelay, TICK_MS, function()
  local ok, why = pcall(tick)
  if not ok then
    reset()
    say("tick error: " .. tostring(why):sub(1, 240))
  end
end)
if not started then
  say("blocked: UE4SS timer registration failed: " .. tostring(err):sub(1, 240))
  return
end
print("[GtaArkLink] loaded; reading " .. PATH .. "\n")
