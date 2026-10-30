-- Operator-owned admission checks. No game APIs or simulated world are implicit.
local env = {}
for _, name in ipairs({"assert", "error", "ipairs", "next", "pairs", "pcall", "select", "tonumber", "tostring", "type", "xpcall",
                       "setmetatable", "getmetatable", "rawequal", "rawget", "rawset", "rawlen"}) do env[name] = _G[name] end
for _, name in ipairs({"math", "string", "table", "utf8"}) do
  env[name] = {}; for k, v in pairs(_G[name]) do env[name][k] = v end
end
local loaded, chunk = pcall(loadfile, assert(arg[1], "subject path required"), "t", env)
local ok, subject = false, nil
if loaded and type(chunk) == "function" then ok, subject = pcall(chunk) end
local caps = {"position", "describe", "candidates", "move_to", "attack", "stop"}
local checks, failures = 0, 0
local function check(name, fn)
  checks = checks + 1
  local ran, passed = pcall(function()
    assert(ok and type(subject) == "table", "module failed to load")
    return fn()
  end)
  local pass = ran and passed == true
  if not pass then failures = failures + 1 end
  print((pass and "[ACCEPTANCE PASS] " or "[ACCEPTANCE FAIL] ") .. name ..
        (pass and "" or " | observed: " .. tostring(passed):gsub("%s+", " "):sub(1, 200)))
end
local function expect(value, reason, want, why)
  assert(value == want and reason == why,
    "value=" .. tostring(value) .. ", reason=" .. tostring(reason) .. "; expected " .. tostring(want) .. ", " .. tostring(why))
  return true
end
local function world()
  local w = {calls = {}, position = {x = 1, y = 2, z = 3}, record = {id = "target", kind = "character"}}
  w.records = {w.record}
  local function saw(name, ...) w.calls[#w.calls + 1] = {name, ...} end
  w.provider = {
    position = function(id) saw("position", id); if w.missing_position then return nil, "position_missing" end; return w.position, "position_ok" end,
    describe = function(id) saw("describe", id); return w.record, "describe_ok" end,
    candidates = function(actor, origin, radius) saw("candidates", actor, origin, radius); if w.missing_candidates then return nil, "candidates_missing" end; return w.records, "candidates_ok" end,
    move_to = function(actor, target) saw("move_to", actor, target); if w.throw then error("provider_command_error") end; return true, "move_ok" end,
    attack = function(actor, target) saw("attack", actor, target); return false, "attack_refused" end,
    stop = function(actor) saw("stop", actor); return nil, "stop_refused" end
  }
  return w
end
local function adapter(w)
  local a, why = subject.new(w.provider)
  assert(type(a) == "table", "new refused complete provider: " .. tostring(why))
  return a
end
local function call_is(w, name, actor, target)
  local c = w.calls[#w.calls]
  assert(#w.calls == 1 and c[1] == name and c[2] == actor and c[3] == target, "provider called with wrong arguments/count")
end

check("legacy admission API exports", function()
  for _, k in ipairs({"new", "get_adapter_type", "init_simulation", "init_real_game", "spawn_raptor"}) do
    assert(type(subject[k]) == "function", "missing export: " .. k)
  end
  return true
end)
check("loading selects no runtime", function() return expect(subject.get_adapter_type(), nil, "uninitialized", nil) end)
check("missing provider rejects", function() local a, e = subject.new(nil); return expect(a, e, nil, "unsupported_runtime") end)
check("non-table providers reject without throwing", function()
  for _, p in ipairs({false, 42, "provider"}) do local a, e = subject.new(p); expect(a, e, nil, "unsupported_runtime") end
  return true
end)
for _, name in ipairs(caps) do
  check("missing capability: " .. name, function()
    local w = world(); w.provider[name] = nil
    local a, e = subject.new(w.provider)
    return expect(a, e, nil, "unsupported_capability:" .. name)
  end)
end
check("admission is passive and does not select a legacy mode", function()
  local w = world(); local a = adapter(w)
  for _, k in ipairs(caps) do assert(type(a[k]) == "function", "adapter missing " .. k) end
  assert(#w.calls == 0, "admission invoked provider")
  return expect(subject.get_adapter_type(), nil, "uninitialized", nil)
end)
check("position returns the direct result and exact actor", function()
  local w = world(); local a = adapter(w); local v, e = a.position("actor")
  call_is(w, "position", "actor"); return expect(v, e, w.position, "position_ok")
end)
check("describe returns the direct record and exact target", function()
  local w = world(); local a = adapter(w); local v, e = a.describe("target")
  call_is(w, "describe", "target"); return expect(v, e, w.record, "describe_ok")
end)
check("candidates preserves array and actor/origin/radius", function()
  local w = world(); local a = adapter(w); local origin = {x = 0, y = 0, z = 0}
  local v, e = a.candidates("actor", origin, 25); local c = w.calls[1]
  assert(#w.calls == 1 and c[1] == "candidates" and c[2] == "actor" and c[3] == origin and c[4] == 25, "enumeration arguments changed")
  return expect(v, e, w.records, "candidates_ok")
end)
check("move preserves true/reason and actor/target", function()
  local w = world(); local a = adapter(w); local v, e = a.move_to("actor", "target")
  call_is(w, "move_to", "actor", "target"); return expect(v, e, true, "move_ok")
end)
check("attack preserves false refusal and actor/target", function()
  local w = world(); local a = adapter(w); local v, e = a.attack("actor", "target")
  call_is(w, "attack", "actor", "target"); return expect(v, e, false, "attack_refused")
end)
check("stop preserves nil refusal and actor", function()
  local w = world(); local a = adapter(w); local v, e = a.stop("actor")
  call_is(w, "stop", "actor"); return expect(v, e, nil, "stop_refused")
end)
check("missing position is never coerced to a table", function()
  local w = world(); w.missing_position = true; local a = adapter(w); local v, e = a.position("actor")
  return expect(v, e, nil, "position_missing")
end)
check("failed enumeration is never coerced to an array", function()
  local w = world(); w.missing_candidates = true; local a = adapter(w); local v, e = a.candidates("actor", w.position, 25)
  return expect(v, e, nil, "candidates_missing")
end)
check("provider exception cannot become command success", function()
  local w = world(); w.throw = true; local a = adapter(w)
  local ran, v, reason = pcall(a.move_to, "actor", "target")
  call_is(w, "move_to", "actor", "target")
  assert(not ran or ((v == nil or v == false) and type(reason) == "string" and #reason > 0), "exception reported success")
  return true
end)
check("simulation requires an explicit provider", function()
  local a, e = subject.init_simulation(nil); expect(a, e, nil, "unsupported_runtime")
  return expect(subject.get_adapter_type(), nil, "uninitialized", nil)
end)
check("explicit simulation admits without invoking runtime", function()
  local w = world(); local a = subject.init_simulation(w.provider)
  assert(type(a) == "table" and type(a.position) == "function" and #w.calls == 0, "simulation admission failed or invoked runtime")
  return expect(subject.get_adapter_type(), nil, "simulation", nil)
end)
check("failed real initialization clears prior simulation", function()
  local w = world(); subject.init_simulation(w.provider)
  local a, e = subject.init_real_game(nil); expect(a, e, nil, "unsupported_runtime")
  return expect(subject.get_adapter_type(), nil, "uninitialized", nil)
end)
check("explicit provider initialization is structural only", function()
  local w = world(); local a = subject.init_real_game(w.provider)
  assert(type(a) == "table" and type(a.position) == "function" and #w.calls == 0, "provider admission failed or invoked runtime")
  return expect(subject.get_adapter_type(), nil, "provider", nil)
end)
check("spawn is explicitly unsupported after admission", function()
  local w = world(); subject.init_real_game(w.provider)
  local v, e = subject.spawn_raptor(w.position, "actor")
  assert(#w.calls == 0, "unsupported spawn invoked provider")
  return expect(v, e, nil, "unsupported_capability:spawn")
end)
check("incomplete simulation rejects and clears prior mode", function()
  local w = world(); subject.init_real_game(w.provider); w.provider.stop = nil
  local v, e = subject.init_simulation(w.provider); expect(v, e, nil, "unsupported_capability:stop")
  return expect(subject.get_adapter_type(), nil, "uninitialized", nil)
end)
print("SMELTER_ACCEPTANCE_CHECKS|{\"checks\":" .. checks .. ",\"failures\":" .. failures .. "}")
os.exit(failures == 0 and 0 or 1)
