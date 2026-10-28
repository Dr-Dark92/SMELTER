-- test_entity_policy.lua: Entity eligibility tests using fake adapters.
package.path = "Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local policy_evaluator = require("entity_policy")

print("[TEST_ENTITY_POLICY] Engine-neutral eligibility evaluator tests\n")

local passed = 0
local failed = 0

local function check(condition, message)
  if condition then
    passed = passed + 1
    print("[PASS] " .. message)
  else
    failed = failed + 1
    print("[FAIL] " .. message)
  end
end

-- Test data: Raptor entity policy
local raptor_policy = {
  allowed_kinds = { character = true },
  blocked_kinds = { vehicle = true },
  required_traits = { human = true },
  any_traits = { npc = true, police = true, player = true }
}

-- Test data: Alternative policy (any character, no trait requirements)
local generic_policy = {
  allowed_kinds = { character = true, vehicle = true },
  blocked_kinds = {}
}

print("=== TEST GROUP 1: Human NPC (should be allowed by Raptor policy) ===")
local npc_entity = {
  id = "NPC_Aaron_001",
  kind = "character",
  traits = { human = true, npc = true },
  valid = true,
  alive = true
}

local allowed, reason = policy_evaluator.evaluate(npc_entity, raptor_policy)
check(allowed == true and reason == "allowed", "Human NPC passes Raptor policy")

print("\n=== TEST GROUP 2: Player character (should be allowed by Raptor policy) ===")
local player_entity = {
  id = "Player_Chaingun_001",
  kind = "character",
  traits = { human = true, player = true },
  valid = true,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(player_entity, raptor_policy)
check(allowed == true and reason == "allowed", "Player passes Raptor policy")

print("\n=== TEST GROUP 3: Police NPC (should be allowed by Raptor policy) ===")
local cop_entity = {
  id = "NPC_Cop_Miller",
  kind = "character",
  traits = { human = true, police = true },
  valid = true,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(cop_entity, raptor_policy)
check(allowed == true and reason == "allowed", "Police NPC passes Raptor policy")

print("\n=== TEST GROUP 4: Vehicle (should be rejected - kind blocked) ===")
local vehicle_entity = {
  id = "Vehicle_Pickup_001",
  kind = "vehicle",
  traits = {},
  valid = true,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(vehicle_entity, raptor_policy)
check(allowed == false and (reason == "kind_blocked" or reason == "kind_not_allowed"), "Vehicle rejected by Raptor policy")

print("\n=== TEST GROUP 5: Invalid entity (should be rejected - valid=false) ===")
local invalid_entity = {
  id = "Dud_Entity_001",
  kind = "character",
  traits = { human = true, npc = true },
  valid = false,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(invalid_entity, raptor_policy)
check(allowed == false and reason == "entity_invalid", "Invalid entity rejected")

print("\n=== TEST GROUP 6: Dead entity (should be rejected - alive=false) ===")
local dead_entity = {
  id = "Corpse_001",
  kind = "character",
  traits = { human = true, npc = true },
  valid = true,
  alive = false
}

allowed, reason = policy_evaluator.evaluate(dead_entity, raptor_policy)
check(allowed == false and reason == "entity_dead", "Dead entity rejected")

print("\n=== TEST GROUP 7: Missing required trait (should be rejected) ===")
local no_human_entity = {
  id = "Alien_001",
  kind = "character",
  traits = { npc = true },
  valid = true,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(no_human_entity, raptor_policy)
check(allowed == false and reason == "missing_required_trait", "Entity without human trait rejected")

print("\n=== TEST GROUP 8: Unknown kind (should be rejected - not in allowed_kinds) ===")
local unknown_kind_entity = {
  id = "Item_001",
  kind = "item",
  traits = {},
  valid = true,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(unknown_kind_entity, raptor_policy)
check(allowed == false and reason == "kind_not_allowed", "Unknown kind rejected")

print("\n=== TEST GROUP 9: Malformed entity (no id) - should be rejected ===")
local malformed_entity = {
  kind = "character",
  traits = {},
  valid = true,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(malformed_entity, raptor_policy)
check(allowed == false and reason == "entity_no_id", "Malformed entity rejected (no id)")

print("\n=== TEST GROUP 10: Policy with different config changes eligibility ===")
local human_npc_with_generic = {
  id = "NPC_John_002",
  kind = "character",
  traits = { npc = true }, -- no human trait
  valid = true,
  alive = true
}

allowed, reason = policy_evaluator.evaluate(human_npc_with_generic, generic_policy)
check(allowed == true and reason == "allowed", "Same entity passes with relaxed policy")

print("\n=== TEST GROUP 11: Malformed policy (not table) - should be rejected ===")
local malformed_policy = "string_instead_of_table"

allowed, reason = policy_evaluator.evaluate(npc_entity, malformed_policy)
check(allowed == false and reason == "policy_not_table", "Malformed policy rejected (not table)")

print("\n=== TEST GROUP 12: Boolean map with non-boolean values (should be rejected) ===")
local invalid_bool_map_policy = {
  allowed_kinds = { character = "yes" }, -- string instead of boolean
  blocked_kinds = {}
}
allowed, reason = policy_evaluator.evaluate(npc_entity, invalid_bool_map_policy)
check(allowed == false and (reason:match("non_boolean") or reason == "policy_not_table"), "Non-boolean values in allowed_kinds rejected")

print("\n=== TEST GROUP 13: Required/any traits as non-table (should be rejected) ===")
local trait_not_table_policy = {
  allowed_kinds = { character = true },
  required_traits = "string"
}
allowed, reason = policy_evaluator.evaluate(npc_entity, trait_not_table_policy)
check(allowed == false and reason == "required_traits_not_table", "Non-table required_traits rejected")

print("\n=== TEST GROUP 14: Conflicting allowed/blocked kinds (block overrides) ===")
local conflict_policy = {
  allowed_kinds = { vehicle = true },
  blocked_kinds = { vehicle = true }
}
allowed, reason = policy_evaluator.evaluate(vehicle_entity, conflict_policy)
check(allowed == false and reason == "kind_blocked", "Explicit block overrides allow for same kind")

print("\n=== TEST GROUP 15: Non-boolean valid flag (numeric) ===")
local numeric_valid_entity = {
  id = "Test_001",
  kind = "character",
  traits = { human = true, npc = true },
  valid = 1, -- number instead of boolean
  alive = true
}
allowed, reason = policy_evaluator.evaluate(numeric_valid_entity, raptor_policy)
check(allowed == false, "Numeric valid flag handled safely (rejected with specific reason or treated as not truly true)")
print("[INFO] Non-boolean valid: " .. tostring(allowed) .. ", reason: " .. reason)

print("\n=== TEST GROUP 16: Mixed boolean/non-boolean flags ===")
local mixed_flags_entity = {
  id = "Test_002",
  kind = "character",
  traits = { human = true, npc = true },
  valid = false,
  alive = "yes" -- string instead of boolean
}
allowed, reason = policy_evaluator.evaluate(mixed_flags_entity, raptor_policy)
check(allowed == false and (reason == "valid_false_alive_mixed_type" or reason == "entity_invalid"), "Mixed type flags rejected")
print("[INFO] Mixed flags: " .. tostring(allowed) .. ", reason: " .. reason)

print("\n=== TEST GROUP 17: Classification overrides misleading IDs/names ===")
local misleading_name_entity = {
  id = "Vehicle_That_Looks_Human",
  kind = "vehicle", -- but named like human
  traits = { human = true },
  valid = true,
  alive = true
}
allowed, reason = policy_evaluator.evaluate(misleading_name_entity, raptor_policy)
check(allowed == false and (reason == "kind_blocked" or reason == "kind_not_allowed"), "ID name cannot override kind classification")
print("[INFO] Misleading name rejected by kind: " .. reason)

print("\n=== TEST GROUP 18: Same entity under two different policies ===")
local consistent_entity = {
  id = "Test_Policy_Switch",
  kind = "character",
  traits = { human = true, npc = true },
  valid = true,
  alive = true
}
allowed1, reason1 = policy_evaluator.evaluate(consistent_entity, raptor_policy)
allowed2, reason2 = policy_evaluator.evaluate(consistent_entity, generic_policy)
check(allowed1 == true and allowed2 == true, "Same entity passes both Raptor and Generic policy")
print("[INFO] Policy switch: Raptor=" .. tostring(allowed1) .. "/" .. reason1 .. ", Generic=" .. tostring(allowed2) .. "/" .. reason2)

print("\n=== TEST GROUP 19: False map entries disabled ===")
local false_entry_policy = {
  allowed_kinds = { character = true, vehicle = false }, -- vehicle explicitly disabled
  blocked_kinds = {},
  required_traits = {}
}
allowed, reason = policy_evaluator.evaluate(vehicle_entity, false_entry_policy)
check(allowed == false and reason == "kind_not_allowed", "False entry in allowed_kinds is treated as disabled")

print("\n=== TEST GROUP 20: required_traits with false entry (must not require trait) ===")
local no_req_policy = {
  allowed_kinds = { character = true },
  blocked_kinds = {},
  required_traits = { human = false }
}
-- Entity missing the disabled-required trait entirely (human trait absent)
local entity_missing_disabled_trait = { id = "Missing_Human_Test", kind = "character", traits = { npc = true }, valid = true, alive = true }
allowed, reason = policy_evaluator.evaluate(entity_missing_disabled_trait, no_req_policy)
check(allowed == true and reason == "allowed", "required_traits with only false values does not impose requirement")

print("\n=== TEST GROUP 21: any_traits with mixed entries (npc alone should fail if only npc=false) ===")
local any_mixed_policy = {
  allowed_kinds = { character = true },
  blocked_kinds = {},
  required_traits = { human = true },
  any_traits = { npc = false, player = true }
}
cop_entity_for_any = { id = "Cop_Test", kind = "character", traits = { human = true, police = true, npc = true }, valid = true, alive = true }
allowed, reason = policy_evaluator.evaluate(cop_entity_for_any, any_mixed_policy)
check(allowed == false and reason == "no_required_trait_match", "npc=false cannot satisfy any_traits")

print("\n=== TEST GROUP 22: Nonboolean trait values in entity (must reject safely during validation) ===")
local bad_trait_entity = {
  id = "Bad_Trait_001",
  kind = "character",
  traits = { human = "yes", npc = 1 }, -- nonboolean trait values
  valid = true,
  alive = true
}
local bad_trait_ran, bad_trait_allowed, bad_trait_reason = pcall(policy_evaluator.evaluate, bad_trait_entity, raptor_policy)
check(bad_trait_ran and bad_trait_allowed == false and type(bad_trait_reason) == "string" and #bad_trait_reason > 0,
  "Nonboolean entity trait values reject safely during validation")

print("\n=== TEST GROUP 23: Nonboolean policy trait map values (must reject safely) ===")
local bad_policy_traits = {
  allowed_kinds = { character = true },
  blocked_kinds = {},
  required_traits = { human = 1 }
}
allowed, reason = policy_evaluator.evaluate(npc_entity, bad_policy_traits)
check(allowed == false and (reason:match("required") or reason == "entity_invalid"), "Nonboolean policy trait values rejected safely")

print("\n=== TEST GROUP 24: Empty required_traits imposes no requirement ===")
local empty_req_policy = {
  allowed_kinds = { character = true },
  blocked_kinds = {},
  required_traits = {}
}
no_human_entity_for_empty = { id = "No_Human_Test", kind = "character", traits = { npc = true }, valid = true, alive = true }
allowed, reason = policy_evaluator.evaluate(no_human_entity_for_empty, empty_req_policy)
check(allowed == true and reason == "allowed", "Empty required_traits imposes no trait requirement")

print("\n=== TEST GROUP 25: Present any_traits with only false entries MUST REJECT ===")
local any_only_disabled_policy = {
  allowed_kinds = { character = true },
  blocked_kinds = {},
  required_traits = {},
  any_traits = { npc = false, player = false }
}
allowed, reason = policy_evaluator.evaluate(npc_entity, any_only_disabled_policy)
check(allowed == false and (reason == "any_traits_all_disabled" or reason == "any_traits_empty"), "Present any_traits with only false entries MUST REJECT")

print("\n=== TEST GROUP 26: Two adapters - raw_to_normalized translates different representations ===")
local function unity_adapter(raw_entity)
  local trait_map = { ["0"] = "human", ["1"] = "npc", ["2"] = "police", ["3"] = "player" }
  local normalized_traits = {}
  if raw_entity.unity_traits then
    for _, idx in ipairs(raw_entity.unity_traits) do
      local name = trait_map[tostring(idx)]
      if name then normalized_traits[name] = true end
    end
  end
  return {
    id = raw_entity.id,
    kind = raw_entity.kind or "character",
    traits = normalized_traits,
    valid = raw_entity.valid == true,
    alive = raw_entity.alive == true
  }
end

local function Rage_adapter(raw_entity)
  local normalized_traits = {}
  if raw_entity.is_human then normalized_traits.human = true end
  if raw_entity.is_npc then normalized_traits.npc = true end
  if raw_entity.is_police then normalized_traits.police = true end
  if raw_entity.is_player then normalized_traits.player = true end
  return {
    id = raw_entity.actor_id or raw_entity.id,
    kind = raw_entity.entity_kind or "character",
    traits = normalized_traits,
    valid = raw_entity.valid and true,
    alive = raw_entity.alive and true
  }
end

-- Both adapters must produce entities with proper traits for raptor_policy (requires human=true)
local unity_raw = { id = "Unity_NPC_001", kind = "character", unity_traits = { "0", "2" }, valid = true, alive = true }
local rage_raw = { actor_id = "Rage_Cop_001", entity_kind = "character", is_human = true, is_police = true, valid = true, alive = true }

local norm1 = unity_adapter(unity_raw)
local norm2 = Rage_adapter(rage_raw)
allowed1, reason1 = policy_evaluator.evaluate(norm1, raptor_policy)
allowed2, reason2 = policy_evaluator.evaluate(norm2, raptor_policy)
check(allowed1 == true and allowed2 == true, "Both adapters produce identical eligibility under same evaluator")

local traits1 = norm1.traits
print("[INFO] Adapter 1 (Unity): traits=(" .. tostring(traits1.human and 1 or 0) .. "," .. tostring(traits1.police and 1 or 0) .. "), result: " .. tostring(allowed1) .. "/" .. reason1)
local traits2 = norm2.traits
print("[INFO] Adapter 2 (RAGE): traits=(" .. tostring(traits2.human and 1 or 0) .. "," .. tostring(traits2.police and 1 or 0) .. "), result: " .. tostring(allowed2) .. "/" .. reason2)

print("\n" .. string.rep("=", 60))
print(string.format("Checks passed: %d/%d", passed, passed + failed))
if failed == 0 then
  print("[RESULT] ALL ENTITY POLICY TESTS PASSED (adapter-portability evidence)")
else
  print("[RESULT] " .. failed .." test(s) failed")
end

os.exit(failed == 0 and 0 or 1)
