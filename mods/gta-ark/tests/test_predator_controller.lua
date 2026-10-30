package.path="Mods/GtaArkLink/Scripts/?.lua;"..package.path
local C=require("predator_controller")
local P=require("entity_policy")

local function run_scenario(role)
  local now=1000
  local command_log={move_count=0,attack_count=0,stop_count=0}
  local world={}
  world.actor={id="actor",kind="creature",traits={},valid=true,alive=true,position={x=0,y=0,z=0}}
  world.veh={id="veh",kind="vehicle",traits={},valid=true,alive=true,position={x=1,y=0,z=0}}
  world.target={id="target",kind="character",traits={human=true},valid=true,alive=true,position={x=5,y=0,z=0}}
  local ctrl,why=C.new{
    adapter={
      position=function(id) return world[id].position end,
      describe=function(id) return world[id] end,
      candidates=function(a,o,r) return{world.veh,world.target} end,
      move_to=function(act,tar) command_log.move_count=command_log.move_count+1; assert(act=="actor"); return true end,
      attack=function(act,tar) command_log.attack_count=command_log.attack_count+1; assert(act=="actor"); return true,"executed" end,
      stop=function(act) command_log.stop_count=command_log.stop_count+1; assert(act=="actor"); return true end
    },
    evaluate=P.evaluate,
    policy={allowed_kinds={character=true},blocked_kinds={vehicle=true},required_traits={human=true}},
    clock=function() return now end,
    profile={detect_radius=10,attack_radius=2,lose_radius=20,attack_cooldown=3}
  }
  assert(ctrl,"constructor must return controller for "..role)
  local r=ctrl:update("actor")
  assert(r.action=="move","initial move toward human target at distance 5")
  assert(command_log.move_count==1,"exactly one initial movement")
  world.target.position.x=1
  r=ctrl:update("actor")
  assert(r.action=="attack","in range attack within radius 2")
  assert(command_log.attack_count==1,"one attack so far")
  now=1001
  r=ctrl:update("actor")
  assert(r.action=="wait","cooldown wait with attack count 1")
  now=1003
  r=ctrl:update("actor")
  assert(r.action=="attack","second attack after cooldown elapsed")
  assert(command_log.attack_count==2,"two attacks total")
  world.target.alive=false
  r=ctrl:update("actor")
  assert(r.action=="lost","target death causes lost")
  assert(command_log.stop_count==1,"stop called once on loss")
end

run_scenario("npc")
run_scenario("police")
run_scenario("player")
print("ALL test assertions passed")