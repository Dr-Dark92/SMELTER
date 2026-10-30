package.path = "Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local S = require("raptor_system_main")
local mode = "table"
local a = {
  position=function() return {x=0,y=0,z=0} end,
  describe=function() return nil end,
  candidates=function() return {} end,
  move_to=function() return true end,
  attack=function() return true end,
  stop=function()
    if mode == "table" then return nil,{code="blocked"} end
    error("probe_stop_exploded")
  end
}
local s, why = S.new({adapter=a,clock=function() return 100 end,
  profile={detect_radius=10,attack_radius=2,lose_radius=20,attack_cooldown=3},
  policy={allowed_kinds={character=true},required_traits={human=true}}})
assert(s, tostring(why))
assert(s:add_actor("actor"))
local ran, value, reason = pcall(s.remove_actor,s,"actor")
assert(ran and value == nil and type(reason)=="string" and #reason>0,
  "nonstring refusal reason must not throw or report success")
assert(s:tick().actor.action == "idle", "failed removal must keep actor")
mode = "throw"
ran,value,reason = pcall(s.remove_actor,s,"actor")
assert(ran and value==nil and type(reason)=="string" and reason:find("probe_stop_exploded",1,true),
  "stop exception detail must survive containment")
assert(s:tick().actor.action == "idle", "throwing removal must keep actor")
print("PASS: structured refusal contained; exact exception clue retained")
