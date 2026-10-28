-- Controller-owned pure-module acceptance. Game/engine names are deliberately absent.
local module_path = assert(arg[1], "subject path required")
local env = {}
for _, name in ipairs({"assert", "error", "ipairs", "next", "pairs", "pcall", "select", "tonumber", "tostring", "type", "xpcall"}) do env[name] = _G[name] end
for _, name in ipairs({"math", "string", "table", "utf8"}) do
  env[name] = {}; for k,v in pairs(_G[name]) do env[name][k] = v end
end
-- No require/debug/io/os/print: subject code cannot replace the verifier or its output.
local loaded, chunk = pcall(loadfile, module_path, "t", env)
local ok, subject = false, nil
if loaded and type(chunk) == "function" then ok, subject = pcall(chunk) end
local evaluate = ok and type(subject) == "table" and subject.evaluate or nil
local checks, failures = 0, 0
local function entity(traits, kind)
  return {id="opaque-id",kind=kind or "character",traits=traits,valid=true,alive=true}
end
local function policy(extra)
  local p={allowed_kinds={character=true}}
  for k,v in pairs(extra or {}) do p[k]=v end
  return p
end
local function check(name, e, p, expected)
  checks=checks+1
  local ran, allowed, reason = pcall(function() return evaluate(e,p) end)
  local passed = ran and type(allowed)=="boolean" and allowed==expected and type(reason)=="string" and #reason>0
  if not passed then failures=failures+1 end
  print((passed and "[ACCEPTANCE PASS] " or "[ACCEPTANCE FAIL] ")..name)
end
check("human NPC allowed",entity({human=true,npc=true}),policy({required_traits={human=true}}),true)
check("player allowed",entity({human=true,player=true}),policy({any_traits={player=true,npc=true}}),true)
check("police NPC allowed",entity({human=true,police=true}),policy({required_traits={human=true}}),true)
check("vehicle kind rejected regardless of name",entity({human=true},"vehicle"),policy(),false)
local invalid=entity({});invalid.valid=false;check("invalid rejected",invalid,policy(),false)
local dead=entity({});dead.alive=false;check("dead rejected",dead,policy(),false)
check("disabled required trait need not exist",entity({}),policy({required_traits={human=false}}),true)
check("empty required map imposes no constraint",entity({}),policy({required_traits={}}),true)
check("absent any map imposes no constraint",entity({}),policy(),true)
check("present empty any map rejects",entity({}),policy({any_traits={}}),false)
check("present all-disabled any map rejects",entity({npc=true}),policy({any_traits={npc=false,player=false}}),false)
check("disabled any entry cannot satisfy active alternatives",entity({npc=true}),policy({any_traits={npc=false,player=true}}),false)
check("active any entry satisfies alternatives",entity({player=true}),policy({any_traits={npc=false,player=true}}),true)
check("queried nonboolean entity trait rejects",entity({human="yes"}),policy({required_traits={human=true}}),false)
check("unused nonboolean entity trait rejects",entity({human=true,extra="yes"}),policy({required_traits={human=true}}),false)
check("nonstring entity trait key rejects",entity({[1]=true}),policy(),false)
check("false required map is malformed",entity({}),policy({required_traits=false}),false)
check("false any map is malformed",entity({}),policy({any_traits=false}),false)
check("false blocked map is malformed",entity({}),policy({blocked_kinds=false}),false)
check("nonboolean allowed-kind entry rejects",entity({}),policy({allowed_kinds={character=true,unused="yes"}}),false)
check("nonboolean blocked-kind entry rejects",entity({}),policy({blocked_kinds={unused="yes"}}),false)
check("nonboolean required-trait entry rejects",entity({human=true}),policy({required_traits={human="yes"}}),false)
check("nonstring required-trait key rejects",entity({}),policy({required_traits={[1]=false}}),false)
local any={alpha=true,beta=true};local first,second
for key in pairs(any) do if not first then first=key else second=key end end
any[second]="yes"
check("all any entries validate before early success",entity({[first]=true}),policy({any_traits=any}),false)
check("nonstring any-trait key rejects",entity({npc=true}),policy({any_traits={npc=true,[1]=false}}),false)
local same=entity({human=true,npc=true})
check("same entity allowed by one policy",same,policy({required_traits={human=true}}),true)
check("same entity rejected by another policy",same,policy({blocked_kinds={character=true}}),false)
check("malformed policy rejects without throwing",entity({}),"invalid",false)
check("malformed entity rejects without throwing",false,policy(),false)
check("missing allowed kinds rejects",entity({}),{},false)
print('SMELTER_ACCEPTANCE_CHECKS|{"checks":'..checks..',"failures":'..failures..'}')
os.exit(failures==0 and 0 or 1)
