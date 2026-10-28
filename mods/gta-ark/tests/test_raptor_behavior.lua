-- test_raptor_behavior.lua: Tests starting chase with proper output verification.
package.path = "Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local raptor_aggro = require("raptor_aggro")

print("[TEST_RAPTOR_BEHAVIOR] Raptor chase controller verification (offline slice)")
print("Module type: " .. type(raptor_aggro))

-- PRE-VALIDATION: module, raptor_states table, and start_chase function must exist
if type(raptor_aggro) ~= "table" then
  print("[FAIL] Module is not a table")
  os.exit(1)
end

if not raptor_aggro.raptor_states or type(raptor_aggro.raptor_states) ~= "table" then
  print("[FAIL] raptor_states is missing or not a table")
  os.exit(1)
end

if raptor_aggro.start_chase and type(raptor_aggro.start_chase) == "function" then
  print("[PASS] start_chase function exists")
else
  print("[FAIL] start_chase is missing or not a function")
  os.exit(1)
end

local tests_passed = 0
local totals_failed = 0

local function check(condition, message)
  if condition then
    tests_passed = tests_passed + 1
    print("[PASS] " .. message)
  else
    totals_failed = totals_failed + 1
    print("[FAIL] " .. message)
  end
end

print("\n=== TEST 1: Fresh Raptor StateCreation (deterministic ID) ===")
local chase_id = "fresh_fixed_2026"
print("Initializing Raptor ID: " .. chase_id)

-- HARDENED: Assert deterministic actor ID has no existing state, do NOT fallback
local existing_state = raptor_aggro.raptor_states[chase_id]
if existing_state then
  print("[EXPECTED FAIL] Existing state found for deterministic ID '" .. chase_id "'")
  print("[RESULT] FRESH_ID_ASSERTION_FAILED")
  totals_failed = totals_failed + 1
else
  -- Call with dot syntax (not colon) since start_chase is a regular function in M table
  local result = raptor_aggro.start_chase(chase_id, "Pawn_NPC_Aaron", {X=50,Y=0,Z=0})
  check(result == true, "start_chase returns true")

  local state = raptor_aggro.raptor_states[chase_id]
  if not state then
    print("[FAIL] No state entry after start_chase")
    check(false, "State must exist in raptor_states after start_chase")
  else
    print("[PASS] State exists for ID: " .. chase_id)
    
    check(type(state.chase_start_time) == "number" and state.chase_start_time > 0, "chase_start_time positive numeric")
    check(state.last_attack_time ~= nil, "last_attack_time is set")
    check(type(state.state) == "string" and state.state == "CHASING", "state.state is CHASING")
  end
end

print("\n" .. string.rep("=", 60))
print("=== RESULTS ===")
print(string.format("Checks passed: %d/%d", tests_passed, tests_passed + totals_failed))
if totals_failed == 0 then
  print("[RESULT] ALL RAPTOR TESTS PASSED (state-creation evidence)")
else
  print("[RESULT] " .. totals_failed .." test(s) failed")
end

os.exit(totals_failed == 0 and 0 or 1)
