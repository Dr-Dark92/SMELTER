-- Engine adapter for Raptor aggression system.
local M = {}

M.adapter_type = "simulation"

function M.init_simulation()
  print("[RaptorAggro] ADAPTER: Simulation mode active")
  M.adapter_type = "simulation"
end

function M.get_adapter_type()
  return M.adapter_type
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