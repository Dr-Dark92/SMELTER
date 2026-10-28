-- Controller-owned pure-module acceptance for a generic predator controller.
-- Game/engine names are deliberately absent. The subject receives an adapter,
-- an eligibility evaluator, a policy, a clock and a tuning profile; it must not
-- read time, files or game APIs itself.
local module_path = assert(arg[1], "subject path required")
local env = {}
for _, name in ipairs({"assert", "error", "ipairs", "next", "pairs", "pcall", "select", "tonumber", "tostring", "type", "xpcall",
                       "setmetatable", "getmetatable", "rawequal", "rawget", "rawset", "rawlen"}) do env[name] = _G[name] end
for _, name in ipairs({"math", "string", "table", "utf8"}) do
  env[name] = {}; for k,v in pairs(_G[name]) do env[name][k] = v end
end
-- No require/debug/io/os/print: subject code cannot replace the verifier or its output.
local loaded, chunk = pcall(loadfile, module_path, "t", env)
local ok, subject = false, nil
if loaded and type(chunk) == "function" then ok, subject = pcall(chunk) end
local new = ok and type(subject) == "table" and subject.new or nil
local load_problem = (not loaded or type(chunk) ~= "function") and ("subject failed to load: " .. tostring(chunk))
  or (not ok and ("subject raised while loading: " .. tostring(subject))) or nil
local checks, failures = 0, 0
-- What the subject actually did, printed beside a failure so the implementer
-- sees observed values instead of only a check name.
local observed = {}
local last_setup = ""
local setup_of = setmetatable({}, {__mode = "k"})
local function saw(text) observed[#observed + 1] = (tostring(text):gsub("%s+", " ")):sub(1, 120) end
local function check(name, fn)
  checks = checks + 1
  observed = {}
  local ran, passed = pcall(fn)
  if not ran then saw("raised: " .. tostring(passed)) end
  passed = ran and passed == true
  if not passed then failures = failures + 1 end
  local detail = (not passed and #observed > 0) and (" | observed: " .. table.concat(observed, "; ", math.max(1, #observed - 2))) or ""
  print((passed and "[ACCEPTANCE PASS] " or "[ACCEPTANCE FAIL] ") .. name .. detail)
end

-- Reference eligibility: normalized kinds/traits only. Vehicles are a kind, never a name.
local function evaluate(entity, policy)
  if type(entity) ~= "table" or type(policy) ~= "table" then return false, "malformed" end
  if entity.valid ~= true then return false, "entity_invalid" end
  if entity.alive ~= true then return false, "entity_dead" end
  if policy.allowed_kinds[entity.kind] ~= true then return false, "kind_not_allowed" end
  return true, "allowed"
end
local POLICY = {allowed_kinds = {character = true}}

-- A fake adapter in a chosen unit scale. Records every command it receives.
local function world(scale)
  local w = {scale = scale, entities = {}, log = {}, fail = {}, throw = {}, hidden = {}, now = 1000}
  function w.put(id, kind, x, alive)
    w.entities[id] = {id = id, kind = kind, traits = {human = kind == "character"}, valid = true,
                      alive = alive ~= false, x = x * scale}
  end
  local function record(id)
    local e = w.entities[id]
    if not e or w.hidden[id] then return nil end
    return {id = e.id, kind = e.kind, traits = e.traits, valid = e.valid, alive = e.alive,
            position = {x = e.x, y = 0, z = 0}}
  end
  local function command(name, actor, target)
    w.log[#w.log + 1] = {name = name, actor = actor, target = target}
    saw("adapter." .. name .. "(" .. tostring(actor) .. ", " .. tostring(target) .. ")")
    if w.throw[name] then error("adapter exploded") end
    if w.fail[name] then return nil, "adapter_refused" end
    return true
  end
  w.adapter = {
    position = function(id) local r = record(id); return r and r.position or nil end,
    describe = function(id)
      saw("adapter.describe(" .. tostring(id) .. ")")
      if w.throw.describe then error("adapter exploded") end
      return record(id)
    end,
    candidates = function(actor_id, origin, radius)
      if w.throw.candidates then saw("adapter.candidates threw"); error("adapter exploded") end
      local out = {}
      for id in pairs(w.entities) do out[#out + 1] = record(id) end  -- deliberately unfiltered
      table.sort(out, function(a, b) return a.id > b.id end)          -- not nearest-first
      return out
    end,
    move_to = function(actor, target) return command("move_to", actor, target) end,
    attack = function(actor, target) return command("attack", actor, target) end,
    stop = function(actor) return command("stop", actor, nil) end,
  }
  function w.count(name, actor, target)
    local n = 0
    for _, c in ipairs(w.log) do
      if c.name == name and (actor == nil or c.actor == actor) and (target == nil or c.target == target) then n = n + 1 end
    end
    return n
  end
  function w.controller(overrides)
    local deps = {adapter = w.adapter, evaluate = evaluate, policy = POLICY, clock = function() return w.now end,
                  profile = {detect_radius = 10 * scale, attack_radius = 2 * scale, lose_radius = 20 * scale, attack_cooldown = 3}}
    local changed = {}
    for k, v in pairs(overrides or {}) do
      deps[k] = v
      local shown = type(v) == "table" and "{...}" or (type(v) == "string" and ("%q"):format(v) or tostring(v))
      changed[#changed + 1] = k .. "=" .. shown
    end
    table.sort(changed)
    last_setup = #changed > 0 and ("[setup " .. table.concat(changed, ", ") .. "] ") or "[valid setup] "
    if type(new) ~= "function" then error(load_problem or "subject module does not export new(deps)") end
    local c, reason = new(deps)
    if c == nil then saw(last_setup .. "new(deps) returned nil, " .. tostring(reason)) end
    if type(c) == "table" then setup_of[c] = last_setup end
    return c, reason
  end
  return w
end

local function step(c, actor)
  if type(c) ~= "table" or type(c.update) ~= "function" then error("controller has no update method") end
  local r = c:update(actor)
  if type(r) == "table" then saw("update(" .. tostring(actor) .. ") -> action=" .. tostring(r.action) .. " target=" .. tostring(r.target_id) .. " reason=" .. tostring(r.reason)) end
  if type(r) ~= "table" or type(r.action) ~= "string" or type(r.reason) ~= "string" or #r.reason == 0 then
    error("update must return {action=string, reason=nonempty string}")
  end
  return r
end
local function rejected(c, reason)
  if c ~= nil then saw((type(c) == "table" and setup_of[c] or last_setup) .. "new(deps) returned a controller; expected nil, reason for this invalid setup") end
  return c == nil and type(reason) == "string" and #reason > 0
end

-- Construction contract.
check("new rejects missing adapter", function() local w = world(1); return rejected(w.controller({adapter = false})) end)
check("new rejects adapter lacking a capability", function()
  local w = world(1); local partial = {}
  for k, v in pairs(w.adapter) do if k ~= "attack" then partial[k] = v end end
  return rejected(w.controller({adapter = partial}))
end)
check("new rejects attack radius beyond detect radius", function()
  local w = world(1)
  return rejected(w.controller({profile = {detect_radius = 1, attack_radius = 2, lose_radius = 3, attack_cooldown = 1}}))
end)
check("new rejects non-function clock and evaluator", function()
  local w = world(1)
  local a, ra = w.controller({clock = 5}); local b, rb = w.controller({evaluate = "yes"})
  return rejected(a, ra) and rejected(b, rb)
end)

local function scenarios(label, scale)
  local function case(name, fn) check(label .. ": " .. name, function() return fn(world(scale)) end) end

  case("no eligible candidate stays idle without commands", function(w)
    w.put("actor", "creature", 0)
    local r = step(w.controller(), "actor")
    return r.action == "idle" and #w.log == 0
  end)
  case("nearest vehicle is rejected; eligible human is chased", function(w)
    w.put("actor", "creature", 0); w.put("car", "vehicle", 1); w.put("walker", "character", 5)
    local r = step(w.controller(), "actor")
    return r.action == "move" and r.target_id == "walker" and w.count("move_to", "actor", "walker") == 1
       and w.count("move_to", nil, "car") == 0 and w.count("attack", nil, "car") == 0
  end)
  case("configured policy and candidate reach the evaluator", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local seen_policy, seen_entity = false, false
    local spy = function(e, p)
      if rawequal(p, POLICY) then seen_policy = true end
      if type(e) == "table" and e.id == "walker" then seen_entity = true end
      return evaluate(e, p)
    end
    step(w.controller({evaluate = spy}), "actor")
    return seen_policy and seen_entity
  end)
  case("evaluator rejection is final even for allowed-looking kinds", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local r = step(w.controller({evaluate = function() return false, "denied" end}), "actor")
    return r.action == "idle" and #w.log == 0
  end)
  case("actor never targets itself", function(w)
    w.put("actor", "character", 0)
    local r = step(w.controller(), "actor")
    return r.action == "idle" and w.count("move_to", nil, "actor") == 0 and w.count("attack", nil, "actor") == 0
  end)
  case("candidate beyond detect radius is ignored", function(w)
    w.put("actor", "creature", 0); w.put("far", "character", 15)
    local r = step(w.controller(), "actor")
    return r.action == "idle" and #w.log == 0
  end)
  case("nearest eligible candidate wins", function(w)
    w.put("actor", "creature", 0); w.put("a", "character", 8); w.put("z", "character", 4)
    local r = step(w.controller(), "actor")
    return r.target_id == "z" and w.count("move_to", "actor", "z") == 1 and w.count("move_to", nil, "a") == 0
  end)
  case("movement is requested once, not every update", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor"); w.now = w.now + 0.1
    local r = step(c, "actor"); w.now = w.now + 0.1; step(c, "actor")
    return r.target_id == "walker" and w.count("move_to") == 1
  end)
  case("attack is issued by the actor at the target in range", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor")
    w.entities.walker.x = 1 * scale
    local r = step(c, "actor")
    return r.action == "attack" and r.target_id == "walker" and w.count("attack", "actor", "walker") == 1
  end)
  case("cooldown uses the injected clock", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 1)
    local c = w.controller(); local first = step(c, "actor")
    w.now = w.now + 1; local waiting = step(c, "actor")
    w.now = w.now + 2; local again = step(c, "actor")
    return first.action == "attack" and waiting.action == "wait" and again.action == "attack"
       and w.count("attack", "actor", "walker") == 2
  end)
  case("target death disengages with stop", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor")
    w.entities.walker.alive = false
    local r = step(c, "actor")
    return r.action == "lost" and w.count("stop", "actor") == 1 and w.count("attack") == 0
  end)
  case("target beyond lose radius disengages", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor")
    w.entities.walker.x = 25 * scale
    local r = step(c, "actor")
    return r.action == "lost" and w.count("stop", "actor") == 1
  end)
  case("target kept between detect and lose radius", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor")
    w.entities.walker.x = 15 * scale
    local r = step(c, "actor")
    return r.action == "move" and r.target_id == "walker" and w.count("stop") == 0
  end)
  case("vanished target disengages and later reacquires", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor")
    w.hidden.walker = true; local lost = step(c, "actor")
    w.hidden.walker = nil; w.put("other", "character", 6); w.now = w.now + 1
    local back = step(c, "actor")
    return lost.action == "lost" and back.action == "move" and back.target_id ~= nil
  end)
  case("refused attack is an error and does not start cooldown", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 1)
    local c = w.controller(); w.fail.attack = true
    local r = step(c, "actor"); w.fail.attack = nil; w.now = w.now + 0.1
    local retry = step(c, "actor")
    return r.action == "error" and retry.action == "attack" and w.count("attack", "actor", "walker") == 2
  end)
  case("throwing adapter is contained as an error", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5); w.throw.move_to = true
    local r = step(w.controller(), "actor")
    return r.action == "error"
  end)
  case("missing actor position issues no commands", function(w)
    w.put("walker", "character", 5)
    local r = step(w.controller(), "ghost")
    return r.action == "error" and #w.log == 0
  end)
  case("two actors keep independent targets and cooldowns", function(w)
    w.put("a1", "creature", 0); w.put("a2", "creature", 100); w.put("t1", "character", 1); w.put("t2", "character", 101)
    local c = w.controller(); local r1 = step(c, "a1"); local r2 = step(c, "a2")
    w.now = w.now + 1; local w1 = step(c, "a1")
    return r1.target_id == "t1" and r2.target_id == "t2" and r1.action == "attack" and r2.action == "attack"
       and w1.action == "wait" and w.count("attack", "a1", "t2") == 0 and w.count("attack", "a2", "t1") == 0
  end)
  case("every command names the actor, never the target, as executor", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor"); w.entities.walker.x = 1 * scale; step(c, "actor")
    w.entities.walker.alive = false; step(c, "actor")
    for _, cmd in ipairs(w.log) do if cmd.actor ~= "actor" then return false end end
    return #w.log == 3
  end)
  -- Added 2026-10-28 after review of a 42/42 subject: every adapter read is
  -- contained, loss is not an attack, and a failed disengage is reported.
  case("throwing candidates or describe is contained", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); w.throw.candidates = true
    local first = step(c, "actor")
    w.throw.candidates = nil; local chase = step(c, "actor")
    w.throw.describe = true; local held = step(c, "actor")
    return first.action == "error" and chase.action == "move" and (held.action == "lost" or held.action == "error")
  end)
  case("losing a target does not start the attack cooldown", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor")
    w.entities.walker.alive = false; local lost = step(c, "actor")
    w.put("other", "character", 1); w.now = w.now + 0.5
    local next_target = step(c, "actor")
    return lost.action == "lost" and next_target.action == "attack" and w.count("attack", "actor", "other") == 1
  end)
  case("refused stop on disengage is reported as an error", function(w)
    w.put("actor", "creature", 0); w.put("walker", "character", 5)
    local c = w.controller(); step(c, "actor")
    w.entities.walker.alive = false; w.fail.stop = true
    local r = step(c, "actor")
    return r.action == "error" and w.count("stop", "actor") == 1 and w.count("attack") == 0
  end)
end

if new then
  scenarios("metre adapter", 1)
  scenarios("centimetre adapter", 100)
else
  -- Keep the fixed check count so a missing constructor is RED, not a count ERROR.
  for _ = 1, 2 * 22 do check("subject exposes new(deps)", function() return false end) end
end
print("SMELTER_ACCEPTANCE_CHECKS|{\"checks\":" .. checks .. ",\"failures\":" .. failures .. "}")
os.exit(failures == 0 and 0 or 1)
