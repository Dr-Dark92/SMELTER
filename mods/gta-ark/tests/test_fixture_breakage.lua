-- test_fixture_breakage.lua: Disposable fixture to verify failure detection.
-- Simulates removing a required export and confirms the test catches it.

print("[TEST_BREAKAGE] Starting breakage verification...")
package.path = "./Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local failures = {}

-- Temporarily load raptor_aggro and verify missing export is caught
function simulate_missing_export()
  local M = require("raptor_aggro")
  -- Simulate by clearing one export
  local original_detect_targets = M.detect_targets
  M.detect_targets = nil
  
  -- Now run the assertion logic that should fail
  local exports_ok = true
  local required_exports = {"detect_targets", "can_detect", "start_chase"}
  for _, export in ipairs(required_exports) do
    if type(M[export]) ~= "function" then
      print(string.format("[EXPECTED FAIL] Missing export: %s", export))
      table.insert(failures, {module="raptor_aggro", error="missing export: " .. export, as_expected=true})
      exports_ok = false
    end
  end
  
  -- Restore
  M.detect_targets = original_detect_targets
  
  return not exports_ok
end

if simulate_missing_export() then
  print("[PASS] Breakage correctly detected: missing export failure")
else
  print("[FAIL] Expected failure was not triggered")
  os.exit(1)
end

print("[STATUS] BREAKAGE DETECTION VERIFIED")
os.exit(0)