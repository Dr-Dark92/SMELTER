-- Generated from operator-pinned predator-system-v1.
-- Verifier SHA256: d121faecc157711292f8475db62c8deba803f9bd8529d853435ac501abf4d122
-- This editable copy does not replace independent frozen acceptance.
local arg = {"Mods/GtaArkLink/Scripts/raptor_system_main.lua"}
-- Operator-owned passive-system/lifecycle contract; no native runtime is supplied.
local path = assert(arg[1], "subject path required")
local base = assert(path:match("^(.*)/[^/]+$"), "subject directory required")
local env, cache = {}, {}
for _, k in ipairs({"assert", "error", "ipairs", "next", "pairs", "pcall", "select", "tonumber", "tostring", "type", "xpcall", "setmetatable", "getmetatable", "rawget", "rawset"}) do env[k] = _G[k] end
for _, k in ipairs({"math", "string", "table", "utf8"}) do env[k] = {}; for n, f in pairs(_G[k]) do env[k][n] = f end end
local native_calls = 0
for _, k in ipairs({"LoopInGameThreadWithDelay", "SpawnActor", "FindFirstOf", "StaticFindObject"}) do
  env[k] = function() native_calls = native_calls + 1; return nil end
end
local imports = {engine_adapter=true, entity_policy=true, predator_controller=true}
env.require = function(name)
  assert(imports[name], "unsupported module: " .. tostring(name))
  if cache[name] then return cache[name] end
  local chunk = assert(loadfile(base .. "/" .. name .. ".lua", "t", env))
  cache[name] = assert(chunk(), "dependency did not return a module")
  return cache[name]
end
local loaded, chunk = pcall(loadfile, path, "t", env)
local ok, subject = false, nil
if loaded and type(chunk) == "function" then ok, subject = pcall(chunk) end
local checks, failures = 0, 0
local function check(name, fn)
  checks = checks + 1
  local ran, value = pcall(function()
    assert(ok and type(subject) == "table" and type(subject.new) == "function", "entry module failed to load/export new")
    return fn()
  end)
  local pass = ran and value == true
  if not pass then failures = failures + 1 end
  print((pass and "[ACCEPTANCE PASS] " or "[ACCEPTANCE FAIL] ") .. name ..
    (pass and "" or " | observed: " .. tostring(value):gsub("%s+", " "):sub(1, 200)))
end
local function world()
  local w = {now=100, log={}, refusal=false, throwing=false, position_throw={}}
  w.entities = {
    actor={id="actor", kind="character", traits={human=false}, valid=true, alive=true, position={x=0,y=0,z=0}},
    other={id="other", kind="character", traits={human=false}, valid=true, alive=true, position={x=0,y=0,z=0}},
    human={id="human", kind="character", traits={human=true}, valid=true, alive=true, position={x=5,y=0,z=0}},
    vehicle={id="vehicle", kind="vehicle", traits={human=false}, valid=true, alive=true, position={x=1,y=0,z=0}}
  }
  local function command(name, actor, target)
    w.log[#w.log+1] = {name, actor, target}
    if name == "stop" and w.throwing then error("stop_exploded") end
    if name == "stop" and w.refusal then return nil, "stop_refused" end
    return true
  end
  w.adapter = {
    position=function(id) if w.position_throw[id] then error("position_exploded") end; local e=w.entities[id]; return e and e.position end,
    describe=function(id) return w.entities[id] end,
    candidates=function() return {w.entities.vehicle, w.entities.human} end,
    move_to=function(a,t) return command("move",a,t) end,
    attack=function(a,t) return command("attack",a,t) end,
    stop=function(a) return command("stop",a) end
  }
  w.deps = {adapter=w.adapter, clock=function() return w.now end,
    profile={detect_radius=10,attack_radius=2,lose_radius=20,attack_cooldown=3},
    policy={allowed_kinds={character=true},blocked_kinds={vehicle=true},required_traits={human=true}}}
  return w
end
local function system(w)
  local s, why = subject.new(w.deps)
  assert(type(s)=="table", "constructor refused complete dependencies: " .. tostring(why))
  for _, k in ipairs({"add_actor","remove_actor","tick"}) do assert(type(s[k])=="function", "missing method "..k) end
  assert(#w.log==0, "constructor issued commands")
  return s
end
local function result(s, id, action)
  local r=s:tick(); assert(type(r)=="table" and type(r[id])=="table", "missing per-actor result")
  assert(r[id].action==action, "expected "..action..", got "..tostring(r[id].action))
  return r[id]
end
local function command(w, name, actor, target)
  local c=w.log[#w.log]
  assert(c and c[1]==name and c[2]==actor and c[3]==target, "wrong command/executor/target")
end
check("module import is passive", function() assert(native_calls==0,"import called native globals"); local w=world();system(w);assert(native_calls==0,"constructor called native globals");return true end)
check("malformed dependencies reject safely", function()
  for _, d in ipairs({false,12,"deps"}) do local s,e=subject.new(d);assert(s==nil and type(e)=="string" and #e>0) end
  local s,e=subject.new(nil);assert(s==nil and type(e)=="string" and #e>0);return true
end)
check("missing runtime fails explicitly", function() local w=world();w.deps.adapter=nil;local s,e=subject.new(w.deps);assert(s==nil and e=="unsupported_runtime");return true end)
check("each missing capability fails before registration", function()
  for _, k in ipairs({"position","describe","candidates","move_to","attack","stop"}) do
    local w=world();w.adapter[k]=nil;local s,e=subject.new(w.deps);assert(s==nil and e=="unsupported_capability:"..k)
  end;return true
end)
check("invalid clock or tuning rejects", function()
  local w=world();w.deps.clock=1;local s,e=subject.new(w.deps);assert(s==nil and type(e)=="string")
  w=world();w.deps.profile.attack_radius=11;s,e=subject.new(w.deps);assert(s==nil and type(e)=="string");return true
end)
check("explicit runtime provider is admitted", function() local w=world();w.deps.runtime=w.adapter;w.deps.adapter=nil;local s=system(w);assert(s:add_actor("actor"));result(s,"actor","move");return true end)
check("invalid explicit adapter never falls back to another provider", function() local w=world();w.deps.runtime=w.adapter;w.deps.adapter=false;local s,e=subject.new(w.deps);assert(s==nil and type(e)=="string");return true end)
check("actor IDs must be nonempty strings", function() local w=world();local s=system(w);for _,id in ipairs({false,12,""}) do local v,e=s:add_actor(id);assert(not v and type(e)=="string") end;local v,e=s:add_actor(nil);assert(not v and type(e)=="string");assert(next(s:tick())==nil);return true end)
check("duplicate actor registration rejects", function() local w=world();local s=system(w);assert(s:add_actor("actor"));local v,e=s:add_actor("actor");assert(not v and type(e)=="string");return true end)
check("empty systems issue no commands", function() local w=world();local s=system(w);assert(next(s:tick())==nil and #w.log==0);return true end)
check("real policy rejects nearer vehicle and chases human", function() local w=world();local s=system(w);assert(s:add_actor("actor"));local r=result(s,"actor","move");assert(r.target_id=="human");command(w,"move","actor","human");return true end)
check("attack and cooldown use real controller and injected clock", function()
  local w=world();w.entities.human.position.x=1;local s=system(w);assert(s:add_actor("actor"));result(s,"actor","attack");command(w,"attack","actor","human")
  local n=#w.log;w.now=101;result(s,"actor","wait");assert(#w.log==n);w.now=103;result(s,"actor","attack");assert(#w.log==n+1);return true
end)
check("target death stops only the actor", function() local w=world();local s=system(w);s:add_actor("actor");result(s,"actor","move");w.entities.human.alive=false;result(s,"actor","lost");command(w,"stop","actor");return true end)
check("removing a string ID stops it and prevents later commands", function() local w=world();local s=system(w);s:add_actor("actor");result(s,"actor","move");assert(s:remove_actor("actor"));command(w,"stop","actor");local n=#w.log;assert(next(s:tick())==nil and #w.log==n);return true end)
check("unknown IDs never receive stop", function() local w=world();local s=system(w);local v,e=s:remove_actor("unknown");assert(not v and type(e)=="string" and #w.log==0);return true end)
check("refused removal retains registration", function() local w=world();local s=system(w);s:add_actor("actor");w.refusal=true;local v,e=s:remove_actor("actor");assert(not v and type(e)=="string");result(s,"actor","move");return true end)
check("throwing removal is contained and retains registration", function() local w=world();local s=system(w);s:add_actor("actor");w.throwing=true;local v,e=s:remove_actor("actor");assert(not v and type(e)=="string");result(s,"actor","move");return true end)
check("re-adding an actor starts a fresh cooldown", function() local w=world();w.entities.human.position.x=1;local s=system(w);s:add_actor("actor");result(s,"actor","attack");assert(s:remove_actor("actor"));assert(s:add_actor("actor"));result(s,"actor","attack");return true end)
check("multiple actors have independent results and executors", function()
  local w=world();w.entities.human.position.x=1;local s=system(w);s:add_actor("actor");s:add_actor("other");local r=s:tick()
  assert(r.actor.action=="attack" and r.other.action=="attack" and #w.log==2);local seen={};for _,c in ipairs(w.log) do assert(c[1]=="attack" and c[3]=="human");seen[c[2]]=true end;assert(seen.actor and seen.other);return true
end)
check("one actor failure cannot hide another actor result", function() local w=world();w.position_throw.actor=true;local s=system(w);s:add_actor("actor");s:add_actor("other");local r=s:tick();assert(r.actor.action=="error" and r.other.action=="move");command(w,"move","other","human");return true end)
print("SMELTER_ACCEPTANCE_CHECKS|{\"checks\":"..checks..",\"failures\":"..failures.."}")
os.exit(failures==0 and 0 or 1)
