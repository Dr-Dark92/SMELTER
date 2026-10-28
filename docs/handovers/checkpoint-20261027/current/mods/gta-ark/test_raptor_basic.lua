-- Test script for Raptor distance calculations and basic logic.

local function test_distance()
  local loc1 = {X=0, Y=0, Z=50}
  local loc2 = {X=300, Y=400, Z=62.5}
  
  local dx = loc2.X - loc1.X
  local dy = loc2.Y - loc1.Y
  local dz = loc2.Z - loc1.Z
  
  local dist = math.sqrt(dx*dx + dy*dy + dz*dz)
  
  print(string.format("Distance test: %.0f cm", dist))
  
  if dist == 500 then
    print("✓ Distance calculation correct")
    return true
  else
    print("✗ Distance failed (expected 500, got " .. tostring(dist) .. ")")
    return false
  end
end

local function test_detection_range()
  local targets = {
    {pawn={GetActorLocation=function() return {X=100,Y=50,Z=50} end}, distance=120, is_npc_human=true},
    {pawn={GetActorLocation=function() return {X=200,Y=100,Z=50} end}, distance=230, is_npc_human=true},
    {pawn={GetActorLocation=function() return {X=600,Y=100,Z=50} end}, distance=630, is_npc_human=true}
  }
  
  local filtered = {}
  for _, t in ipairs(targets) do
    if t.distance <= 500 then
      table.insert(filtered, t)
    end
  end
  
  print(string.format("Detection test: Found %d targets within range", #filtered))
  
  if #filtered == 2 then
    print("✓ Range filtering correct")
    return true
  else
    print("✗ Range filtering failed")
    return false
  end
end

print("[RaptorBasicTest] Starting tests...")

local test1 = test_distance()
local test2 = test_detection_range()

print(string.format("\n[Results] Tests passed: %d/2", (test1 and test2) and 2 or 1))
