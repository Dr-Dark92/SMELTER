-- test_raptor_modules.lua: Direct import and function verification.
-- This test imports the actual raptor modules from the correct paths
-- and verifies they compile successfully with valid exports.

print("[TEST] Starting Lua module compilation checks...")
package.path = "./Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local tests_passed = 0
local tests_failed = 0
local failures = {}

local function check_module(name)
  print(string.format("Checking: %s", name))
  local f, err = require(name)
  
  if not f then
    print(string.format("[FAIL] Cannot load %s: %s", name, tostring(err)))
    tests_failed = tests_failed + 1
    table.insert(failures, {module=name, error=tostring(err)})
    return false
  end
  
  -- Execute the module to get exports
  local M = f
  if not M then
    print(string.format("[FAIL] %s did not return a module table", name))
    tests_failed = tests_failed + 1
    table.insert(failures, {module=name, error="no export"})
    return false
  end
  
  -- Assert expected exports for raptor_aggro (nine controller functions)
  if name == "raptor_aggro" then
    local required_exports = {
      "detect_targets",
      "can_detect",
      "start_chase",
      "update_chase",
      "attempt_attack",
      "update_idle",
      "cleanup_raptor",
      "distance_between",
      "deg_to_rad"
    }
    
    for _, export in ipairs(required_exports) do
      if type(M[export]) ~= "function" then
        print(string.format("[FAIL] %s missing required export: %s", name, export))
        tests_failed = tests_failed + 1
        table.insert(failures, {module=name, error="missing export: " .. export})
        return false
      end
    end
    print(string.format("[PASS] %s has all %d required exports", name, #required_exports))
  
  -- Assert expected exports for engine_adapter (derived from actual interface)
  elseif name == "engine_adapter" then
    local required_exports = {"init_simulation", "init_real_game", "get_adapter_type", "spawn_raptor"}
    for _, export in ipairs(required_exports) do
      if type(M[export]) ~= "function" then
        print(string.format("[FAIL] %s missing required export: %s", name, export))
        tests_failed = tests_failed + 1
        table.insert(failures, {module=name, error="missing export: " .. export})
        return false
      end
    end
    print(string.format("[PASS] %s has all %d required exports", name, #required_exports))
  
  -- Check entry-point module (raptor_system_main) for successful load
  elseif name == "raptor_system_main" then
    print(string.format("[PASS] %s loads as entry point successfully", name))
  end
  
  print(string.format("[PASS] %s executes successfully with valid exports", name))
  tests_passed = tests_passed + 1
  return true
end

-- Check all three core modules using bare require names
check_module("raptor_aggro")
check_module("engine_adapter")
check_module("raptor_system_main")

print(string.rep("=", 60))
print(string.format("[RESULTS] Passed: %d/%d, Failed: %d/%d", tests_passed, tests_passed + tests_failed, tests_failed, tests_passed + tests_failed))

if #failures > 0 then
  print("\nDetailed failures:")
  for _, f in ipairs(failures) do
    print(string.format("  - %s: %s", f.module, f.error))
  end
  os.exit(1)
end

print("[STATUS] ALL MODULES COMPILE AND RUN SUCCESSFULLY")
os.exit(0)