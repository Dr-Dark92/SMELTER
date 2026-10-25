-- ARK side of the GTA -> ARK camera link (M1), a UE4SS Lua mod. Every ~33 ms on the game
-- thread it reads the GAL1 record and moves the local view to follow GTA's camera.
--
-- UNVERIFIED IN THE GAME: UE4SS on ARK's UE 5.5 build, the PlayerController/camera calls and
-- the view-moving method below have not run yet. The first in-game session chooses method (a)
-- or (b) from docs/discovery/GTA_ARK_M1_DESIGN.md and records the result in MODLOG.md.
local link = require("gal_link")

local PATH = link.default_path()
local TICK_MS = 33
local tracker = link.new_tracker(30)  -- about 1 s of unchanged sequence
local origin = nil                     -- captured at link start: GTA and ARK poses
local state = "waiting"

local function say(controller, text)
  if state == text then return end
  state = text
  print("[GtaArkLink] " .. text .. "\n")
  pcall(function() controller:ClientMessage("GTA link: " .. text) end)
end

local function controller()
  local pc = FindFirstOf("PlayerController")  -- nil on the main menu
  if pc and pc:IsValid() then return pc end
  return nil
end

local function capture_origin(pc, record)
  local cam = pc.PlayerCameraManager
  local loc, rot = cam:GetCameraLocation(), cam:GetCameraRotation()
  origin = {gta = record.cam_pos, gta_yaw = record.cam_rot[3],
            ue = {loc.X, loc.Y, loc.Z}, ue_yaw = rot.Yaw}
end

-- Method (a): turn the controller and move the pawn (single-player ghost/fly expected).
-- Method (b), a spawned camera actor as view target, replaces this if (a) misbehaves.
local function apply(pc, location, rotation)
  pc:SetControlRotation({Pitch = rotation[1], Yaw = rotation[2], Roll = rotation[3]})
  local pawn = pc.Pawn
  if pawn and pawn:IsValid() then
    pawn:K2_SetActorLocation({X = location[1], Y = location[2], Z = location[3]}, false, {}, true)
  end
end

local function tick()
  local pc = controller()
  if not pc then origin = nil; return end
  local record = link.read(PATH)
  local stale = link.observe(tracker, record)
  if stale or not record or record.flags & link.FLAG_ENABLED == 0 then
    origin = nil  -- give ARK its own camera back; recapture when the link resumes
    say(pc, record and not stale and "paused in GTA (F7)" or (tracker.last and "stale" or "waiting"))
    return
  end
  if not origin then capture_origin(pc, record) end
  local location, rotation = link.to_unreal(record.cam_pos, record.cam_rot, origin.gta,
                                            origin.gta_yaw, origin.ue, origin.ue_yaw)
  apply(pc, location, rotation)
  say(pc, "following")
end

LoopInGameThreadWithDelay(TICK_MS, function()
  local ok, err = pcall(tick)  -- an error inside a loop callback would silently end the loop
  if not ok then print("[GtaArkLink] tick error: " .. tostring(err) .. "\n") end
end)
print("[GtaArkLink] loaded; reading " .. PATH .. "\n")
