-- Raptor aggression prototype with cougar behavior baseline.
local M = {}

M.config = {
  detection_range_cm = 500,
  chase_range_cm = 1000,
  melee_range_cm = 300,
  attack_damage = 25,
  attack_cooldown_sec = 1.5,
  disengagement_range_cm = 800,
  max_chase_time_sec = 10,
  turn_speed_deg_per_sec = 90,
  move_speed_cm_per_sec = 550
}

M.raptor_states = {}

function M.detect_targets(raptor_id, current_location)
  local detected = {}
  
  local GameStateBase = SystemInfo.GameInstance and SystemInfo.GameInstance:GetGameState()
  if not GameStateBase then return detected end
  
  for _, pawn in ipairs(GameStateBase.PlayerArray or {}) do
    if not pawn:IsValid() then goto continue_loop; end
    
    local pawn_loc = pawn:GetActorLocation()
    if not pawn_loc then goto continue_loop; end
    
    local dist = M.distance_between(current_location, {X=pawn_loc.X, Y=pawn_loc.Y, Z=pawn_loc.Z})
    
    if dist < M.config.detection_range_cm then
      table.insert(detected, {pawn = pawn, distance = dist})
    end
    ::continue_loop::
  end
  
  return detected
end

function M.init_raptor(raptor_id)
  if not raptor_id or type(raptor_id) ~= "string" then return false end
  if M.raptor_states[raptor_id] then return false end
  
  M.raptor_states[raptor_id] = {
    id = raptor_id,
    health = 100,
    max_health = 100,
    state = "IDLE",
    chase_start_time = 0,
    last_attack_time = 0
  }
  return true
end

function M.can_detect(raptor_id)
  local state = M.raptor_states[raptor_id]
  return type(state) == "table" and not state.is_attacking
end

function M.start_chase(raptor_id, target_pawn, initial_location)
  if not raptor_id or type(raptor_id) ~= "string" then return false end
  
  local state = M.raptor_states[raptor_id]
  if not state then
    local fresh_state = {
      id = raptor_id,
      health = 100,
      max_health = 100,
      state = "CHASING",
      chase_start_time = os.time(),
      last_attack_time = 0,
      target_id = type(target_pawn) == "string" and target_pawn or nil
    }
    M.raptor_states[raptor_id] = fresh_state
    state = fresh_state
  end
  
  if initial_location and initial_location.X then
    state.target_pos = initial_location
  end
  state.state = "CHASING"
  state.chase_start_time = os.time()
  
  return true
end

function M.update_idle(raptor_id)
  return type(M.raptor_states[raptor_id]) == "table"
end

function M.attempt_attack(raptor_id)
  local state = M.raptor_states[raptor_id]
  if not state or state.state ~= "CHASING" then return false end
  local now = os.time()
  if now - state.last_attack_time < M.config.attack_cooldown_sec then return false end
  state.is_attacking = true
  state.last_attack_time = now
  return true
end

function M.cleanup_raptor(raptor_id)
  local state = M.raptor_states[raptor_id]
  if not state then return false end
  state.state = "IDLE"
  return true
end

function M.update_chase(raptor_id, current_tick)
  local state = M.raptor_states[raptor_id]
  if not state or state.state ~= "CHASING" then return false end
  state.last_update_time = current_tick or os.time()
  return true
end

function M.distance_between(loc1, loc2)
  if not loc1 or not loc2 then return math.huge end
  local x1 = loc1.X or 0
  local y1 = loc1.Y or 0
  local z1 = loc1.Z or 0
  local x2 = loc2.X or 0
  local y2 = loc2.Y or 0
  local z2 = loc2.Z or 0
  return math.sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)
end

function M.deg_to_rad(degrees)
  return degrees * (math.pi / 180.0)
end

return M