-- Run actual main.lua with synthetic engine objects, never a game.
local output = print
package.path = "ark/Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local link = require("gal_link")
local real_read, errors, checks = link.read, 0, 0
local function check(ok, message)
  checks = checks + 1
  if not ok then errors = errors + 1; output("FAIL " .. message) end
end

local function fixture(options)
  options = options or {}
  local callback, record = nil, nil
  local moves, rotations, logs, messages = {}, {}, {}, {}
  local function pawn(address)
    return {IsValid = function() return true end, GetAddress = function() return address end,
      K2_GetActorLocation = function() return {X=5000,Y=-3000,Z=1200} end,
      K2_SetActorLocation = function(_, position)
        if options.throw_move then error("synthetic engine fault", 0) end
        moves[#moves+1] = position; return options.move_ok ~= false
      end}
  end
  local pc = {Pawn = pawn(20), IsValid = function() return true end,
    GetAddress = function() return 10 end, IsLocalPlayerController = function() return true end,
    PlayerCameraManager = {IsValid = function() return true end,
      GetCameraRotation = function() return {Yaw=90} end,
      GetCameraLocation = function() error("must not anchor pawn to camera") end},
    SetControlRotation = function(_, rotation) rotations[#rotations+1] = rotation end,
    ClientMessage = function(_, text) messages[#messages+1] = text end}
  local remote = {IsValid=function() return true end, IsLocalPlayerController=function() return false end}
  local env = setmetatable({require=require, print=function(text) logs[#logs+1] = text end,
    FindAllOf=function(name)
      assert(name=="PlayerController"); return options.no_players and {} or {remote,pc}
    end,
    StaticFindObject=function(name)
      assert(name=="/Script/Engine.Default__KismetSystemLibrary")
      return {IsValid=function() return true end, IsStandalone=function(_, player)
        assert(player==pc)
        if options.unknown_network then error("network API unavailable",0) end
        return options.networked~=true
      end}
    end,
    LoopInGameThreadWithDelay=function(delay,fn) assert(delay==33);callback=fn;return 42 end,
  },{__index=_G})
  if options.no_timer then env.LoopInGameThreadWithDelay=false end
  link.read=function() return record end
  assert(loadfile("ark/Mods/GtaArkLink/Scripts/main.lua","t",env))()
  return {pc=pc,options=options,moves=moves,rotations=rotations,logs=logs,messages=messages,
    tick=function() callback() end,has_timer=function() return callback~=nil end,
    set_record=function(sequence,flags,north)
      record={sequence=sequence,flags=flags or 3,cam_pos={100,200+(north or 0),30},cam_rot={0,0,0}}
    end,respawn=function() pc.Pawn=pawn(21) end}
end

local f=fixture();f.set_record(2);f.tick()
check(#f.moves==1 and #f.rotations==1,"local standalone player follows")
check(f.moves[1].Z==1200,"camera eye offset is not added to pawn")
f.set_record(4,3,1);f.tick()
check(f.moves[2].X==5100,"subsequent camera displacement is applied")
f.respawn();f.set_record(6,3,2);f.tick()
check(f.moves[3].X==5000,"respawn captures new origin")
for _=1,31 do f.tick() end
local count=#f.moves;f.tick()
check(#f.moves==count,"stale data stops mutations")
for _,options in ipairs({{networked=true},{unknown_network=true},{no_players=true}}) do
  local blocked=fixture(options);blocked.set_record(2);blocked.tick();blocked.tick()
  check(#blocked.moves==0 and #blocked.rotations==0,"unknown or remote session cannot mutate view")
end
for _,flags in ipairs({0,1,2}) do
  local paused=fixture();paused.set_record(2,flags);paused.tick()
  check(#paused.moves==0 and #paused.rotations==0,"both Story Mode and enabled flags required")
end
local failed=fixture({move_ok=false});failed.set_record(2);failed.tick()
check(#failed.rotations==0,"failed movement does not rotate view")
check(not table.concat(failed.logs):find("following",1,true),"no false following message")
local fault=fixture({throw_move=true});fault.set_record(2);fault.tick();local logged=#fault.logs;fault.tick()
check(#fault.logs==logged,"repeating error does not flood logs")
fault.options.throw_move=false;fault.set_record(4);fault.tick()
check(#fault.rotations==1,"engine exception does not kill callback")
local missing=fixture({no_timer=true})
check(not missing.has_timer() and table.concat(missing.logs):find("timer API",1,true),"missing timer API is reported")
link.read=real_read
output("test_ark_runtime.lua: "..checks.." checks; "..errors.." failures")
os.exit(errors==0 and 0 or 1)
