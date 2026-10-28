local M = {}

local function is_boolean(v) return v == true or v == false end
local function is_bool_map(t)
  if type(t) ~= "table" then return false end
  for _, v in pairs(t) do if type(v) ~= "boolean" then return false end end
  return true
end

local function validate_entity(e)
  if type(e) ~= "table" then return false, "entity_not_table" end
  if not e.id or type(e.id) ~= "string" then return false, "entity_no_id" end
  if not e.kind or type(e.kind) ~= "string" then return false, "entity_no_kind" end
  if not e.traits or type(e.traits) ~= "table" then return false, "entity_no_traits" end
  
  -- Verify ALL entity-trait keys and values: string keys, boolean values (false allowed but doesn't participate in checks)
  for k, v in pairs(e.traits) do
    if type(k) ~= "string" then return false, "entity_traits_non_string_key" end
    if type(v) ~= "boolean" then return false, "entity_traits_non_boolean_value" end
  end
  
  -- Validate valid/alive flags - must both be boolean types OR consistent mixed types
  local v_bool = is_boolean(e.valid)
  local a_bool = is_boolean(e.alive)
  
  -- If one is boolean and the other isn't, check which value is false -> return appropriate error
  if v_bool and not a_bool then
    if e.valid == false then return false, "valid_false_alive_mixed_type" end
    return false, "valid_true_alive_not_bool"
  end
  if a_bool and not v_bool then
    if e.alive == false then return false, "alive_false_valid_mixed_type" end
    return false, "alive_true_valid_not_bool"
  end
  
  -- Both non-boolean: check for mixed true values (treat as valid/alive flag issues)
  if not v_bool and not a_bool then
    if e.valid == true or e.alive == true then 
      return false, "valid_true_alive_not_bool"
    end
  end
  
  return true, nil
end

local function validate_policy(p)
  if type(p) ~= "table" then return false, "policy_not_table" end
  if not p.allowed_kinds or type(p.allowed_kinds) ~= "table" then return false, "policy_no_allowed_kinds" end
  
  -- Validate allowed_kinds: string keys, boolean values; only true entries count
  for k, v in pairs(p.allowed_kinds) do
    if type(k) ~= "string" then return false, "allowed_kinds_non_string_key" end
    if type(v) ~= "boolean" then return false, "allowed_kinds_non_boolean_value" end
  end
  
  -- Validate blocked_kinds: string keys, boolean values; false only
  if p.blocked_kinds ~= nil then
    if type(p.blocked_kinds) ~= "table" then return false, "blocked_kinds_not_table" end
    for k, v in pairs(p.blocked_kinds) do
      if type(k) ~= "string" then return false, "blocked_kinds_non_string_key" end
      if type(v) ~= "boolean" then return false, "blocked_kinds_non_boolean_value" end
    end
  end
  
  -- Validate required_traits: string keys, boolean values; false only
  if p.required_traits ~= nil then
    if type(p.required_traits) ~= "table" then return false, "required_traits_not_table" end
    for k, v in pairs(p.required_traits) do
      if type(k) ~= "string" then return false, "required_traits_non_string_key" end
      if type(v) ~= "boolean" then return false, "required_traits_non_boolean_value" end
    end
  end
  
  if p.any_traits and type(p.any_traits) ~= "table" then return false, "any_traits_not_table" end

  -- Present any_traits must be a table; absent (nil) allowed, empty/all-disabled rejects
  if p.any_traits ~= nil then
    if type(p.any_traits) ~= "table" then return false, "any_traits_not_table" end
    for k, v in pairs(p.any_traits) do
      if type(k) ~= "string" then return false, "any_traits_non_string_key" end
      if type(v) ~= "boolean" then return false, "any_traits_non_boolean_value" end
    end
    
    -- Present any_traits={} MUST REJECT (empty table)
    if not next(p.any_traits) then return false, "any_traits_empty" end
    
    -- Present any_traits with ONLY false entries MUST REJECT (frozen contract)
    local has_any_true = false
    for _, v in pairs(p.any_traits) do
      if v == true then has_any_true = true break end
    end
    if not has_any_true then return false, "any_traits_all_disabled" end
  end

  return true, nil
end

function M.evaluate(entity, policy)
  local ok, err = validate_entity(entity); if not ok then return false, err end
  local ok2, err2 = validate_policy(policy); if not ok2 then return false, err2 end
  
  local valid_flag = entity.valid == true
  local alive_flag = entity.alive == true
  if not valid_flag then return false, "entity_invalid" end
  if not alive_flag then return false, "entity_dead" end
  
  if policy.blocked_kinds and policy.blocked_kinds[entity.kind] then return false, "kind_blocked" end
  if not policy.allowed_kinds[entity.kind] then return false, "kind_not_allowed" end
  
  -- Trait-based eligibility: require all traits with boolean=true, reject if none match for any_traits with at least one true entry
  local req = policy.required_traits
  if req then
    for trait_key, value in pairs(req) do
      if type(trait_key) ~= "string" or type(value) ~= "boolean" then return false, "required_trait_invalid_entry" end
      if value == true then
        -- Require trait must exist and have boolean=true value
        local trait_val = entity.traits[trait_key]
        if not trait_val or type(trait_val) ~= "boolean" or trait_val ~= true then return false, "missing_required_trait" end
      end
    end
  end
  
  local any = policy.any_traits
  if any and next(any) then
    local has_enabled = false
    for trait_key, value in pairs(any) do
      if type(trait_key) ~= "string" or type(value) ~= "boolean" then return false, "any_trait_invalid_entry" end
      if value == true then has_enabled = true break end
    end
    if has_enabled then
      local found = false
      for trait_key, value in pairs(any) do
        if value == true then
          local trait_val = entity.traits[trait_key]
          if trait_val and type(trait_val) == "boolean" and trait_val == true then found = true break end
        end
      end
      if not found then return false, "no_required_trait_match" end
    end
  end
  
  return true, "allowed"
end

return M