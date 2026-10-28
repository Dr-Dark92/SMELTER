-- Engine adapter for Raptor aggression system.
-- Replaceable interface allowing simulation or real_game modes.

local M = {}

M.adapter_type = "simulation"

-- Initialize simulated mode (offline testing)
function M.init_simulation()
  print("[RaptorAggro] ADAPTER: Simulation mode active")
  M.adapter_type = "simulation"
end

-- Initialize real ARK mode with UE4SS integration
function M.init_real_game()
  local ok, err = pcall(function()
    if type(LoopInGameThreadWithDelay) ~= "function" then
      error("UE4SS LoopInGameThreadWithDelay API unavailable")
    end
    
    local GameStateBase = SystemInfo and SystemInfo.GameInstance and SystemInfo.GameInstance:GetGameState()
    if not GameStateBase then
      error("Cannot find GameStateBase in current session")
    end
    
    M.adapter_type = "real_ark"
  end)
  
  if not ok then
    M.adapter_type = "simulation"
  end
end

function M.get_adapter_type()
  return M.adapter_type
end

-- Spawn raptor (simulated or real depending on mode)
function M.spawn_raptor(location, raptor_id)
  if M.adapter_type == "real_ark" then
    local spawner = StaticFindObject and StaticFindObject("/Script/Engine.Default__ObjectInitializer")
    if not spawner then return false end
    -- Real spawn would go here (needs ARK AI integration data)
    
  else
    M.spawned_id = raptor_id or math.random(1000, 9999)
  end
  
  return true
end

function M.get_valid_targets(location)
  if M.adapter_type == "real_ark" then
    return get_game_targets and get_game_targets(location) or {}
  else
    return M.simulate_targets(location)
  end
end

function M.distance_between(loc1, loc2)
  local dx = loc2.X - loc1.X
  local dy = loc2.Y - loc1.Y
  local dz = loc2.Z - loc1.Z
  return math.sqrt(dx*dx + dy*dy + dz*dz)
end

function M.simulate_targets(location)
  local targets = {}
  for i=1,3 do
    local d = i * 150
    local tl = {X=location.X+d, Y=location.Y, Z=location.Z}
    table.insert(targets, {
      pawn={GetActorLocation=function() return tl end, IsValid=function() return true end},
      distance=d,
      is_npc_human=true,
      priority=1
    })
  end
  return targets
end

return M