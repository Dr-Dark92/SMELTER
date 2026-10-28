-- Raptor aggression system main loop.
-- Integrates Cougar behavior prototype with engine adapter pattern.

local raptor_aggro = require("raptor_aggro")
local engine_adapter = require("engine_adapter")

print("[RaptorAggro] LOADED; initializing...")

-- Game state tracking
local active_raptor_ids = {}

-- Initialize simulation mode by default
engine_adapter.init_simulation()

function tick()
  local pc = FindFirstOf and FindFirstOf("PlayerController")
  
  if type(LoopInGameThreadWithDelay) ~= "function" then
    print("[RaptorAggro] BLOCKED: UE4SS timer API unavailable")
    return
  end
  
  if not pc or not pc:IsValid() then
    local system = StaticFindObject and StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    if not system then
      print("[RaptorAggro] Waiting for game session")
      return
    end
  end
  
  ensure_simulation_mode_ready()
  update_all_instances()
end

function ensure_simulation_mode_ready()
  if #active_raptor_ids < 2 then
    -- Try to get player pawn
    local pc = FindFirstOf and FindFirstOf("PlayerController")
    if not pc or not pc:IsValid() then return end
    
    local pawn_get = pc.GetPawn
    if not pawn_get then return end
    
    local p = pawn_get(pc)
    if not p then return end
    
    local loc_get = p.GetActorLocation
    if not loc_get then return end
    
    local loc = loc_get(p)
    if not loc then return end
    
    -- Spawn test raptors (simulation mode)
    for i=1, 2 do
      local spawn_loc = {
        X=loc.X+(i*150),
        Y=loc.Y+(i%2==0 and 100 or -100),
        Z=loc.Z+(i*25)
      }
      
      local id = "sim_"..os.time().."_"..i
      if raptor_aggro.spawn_raptor(spawn_loc, id) then
        table.insert(active_raptor_ids, id)
        print(string.format("[RaptorAggro] Spawned simulation raptor %s at (%.0f,%.0f,%.0f)", id, spawn_loc.X, spawn_loc.Y, spawn_loc.Z))
      end
    end
  end
end

function update_all_instances()
  for _, rid in ipairs(active_raptor_ids) do
    local state = raptor_aggro.raptor_states[rid]
    if not state then goto continue end
    if state.state == "OFFLINE" then
      table.remove(active_raptor_ids, rid)
      goto continue
    end
    
    -- Update idle/chase logic (placeholder location)
    raptor_aggro.update_idle(rid, {X=0,Y=0,Z=50})
    ::continue::
  end
end

-- Main startup
if type(LoopInGameThreadWithDelay) == "function" then
  local ok, err = pcall(LoopInGameThreadWithDelay, 33, tick)
  if not ok then
    print(string.format("[RaptorAggro] FAILED: %s", tostring(err)))
  else
    print("[RaptorAggro] LOADED - running raptor aggression system")
  end
else
  print("[RaptorAggro] BLOCKED: Cannot start without UE4SS timer API")
end
