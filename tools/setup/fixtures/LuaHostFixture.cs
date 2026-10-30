// Operator-reviewed offline fixture. No RPH reference, game or real native provider.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using KeraLua;
using Smelter.ManagedLua;

public static class LuaHostFixture
{
    private static void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
    private static void Failure(Action action, string expected) {
        try { action(); } catch (Exception error) {
            Check(error.Message.Contains(expected), "wrong failure: " + error.Message); return;
        }
        throw new Exception("missing failure: " + expected);
    }
    private static Dictionary<string,string> Modules(string root) {
        var modules = new Dictionary<string,string>();
        foreach (string name in new [] {"engine_adapter", "entity_policy", "predator_controller", "raptor_system_main"})
            modules[name] = File.ReadAllText(Path.Combine(root, "subjects", name + ".lua"), Encoding.UTF8);
        return modules;
    }
    private static LuaModuleHost Small(string source = "return {}", int budget = 200000, int callbackMs = 100) {
        return new LuaModuleHost(new Dictionary<string,string>{{"probe",source}}, budget, callbackMs);
    }
    private static void Position(Lua lua, double x) {
        lua.NewTable(); lua.PushNumber(x); lua.SetField(-2,"x");
        lua.PushNumber(0); lua.SetField(-2,"y"); lua.PushNumber(0); lua.SetField(-2,"z");
    }
    private static void Entity(Lua lua, string id, string kind, double x, bool human, bool alive) {
        lua.NewTable(); lua.PushString(id); lua.SetField(-2,"id"); lua.PushString(kind); lua.SetField(-2,"kind");
        lua.PushBoolean(true); lua.SetField(-2,"valid"); lua.PushBoolean(alive); lua.SetField(-2,"alive");
        Position(lua,x); lua.SetField(-2,"position"); lua.NewTable();
        lua.PushBoolean(human); lua.SetField(-2,"human"); lua.SetField(-2,"traits");
    }
    private static string ActionOf(object value) {
        var results = (Dictionary<object,object>)value;
        return (string)((Dictionary<object,object>)results["actor"])["action"];
    }
    private static void Gameplay(string root) {
        double distance=5, now=100; bool alive=true; var log=new List<string>();
        using (var host = new LuaModuleHost(Modules(root))) {
            Check(host.Version=="Lua 5.4","wrong interpreter");
            host.SetCallback("host_clock", delegate(IntPtr p) { var l=Lua.FromIntPtr(p); l.PushNumber(now); return 1; });
            host.SetCallback("host_position", delegate(IntPtr p) { var l=Lua.FromIntPtr(p); Check(l.ToString(1)=="actor","wrong actor position"); Position(l,0); return 1; });
            host.SetCallback("host_describe", delegate(IntPtr p) { var l=Lua.FromIntPtr(p); Check(l.ToString(1)=="npc","wrong described target"); Entity(l,"npc","character",distance,true,alive); return 1; });
            host.SetCallback("host_candidates", delegate(IntPtr p) { var l=Lua.FromIntPtr(p); Check(l.ToString(1)=="actor","wrong enumeration actor");
                l.NewTable(); Entity(l,"vehicle","vehicle",0.5,false,true); l.RawSetInteger(-2,1);
                Entity(l,"npc","character",distance,true,alive); l.RawSetInteger(-2,2); return 1; });
            foreach (string name in new [] {"move_to","attack","stop"}) {
                string captured=name;
                host.SetCallback("host_"+name, delegate(IntPtr p) { var l=Lua.FromIntPtr(p);
                    Check(l.GetTop()==(captured=="stop" ? 1 : 2),"wrong command arity");
                    log.Add(captured+":"+l.ToString(1)+":"+(captured=="stop" ? "" : l.ToString(2))); l.PushBoolean(true); return 1; });
            }
            Check(log.Count==0,"construction issued commands");
            object[] result=host.Execute(@"
local E=require('raptor_system_main')
system=assert(E.new({adapter={position=host_position,describe=host_describe,candidates=host_candidates,
 move_to=host_move_to,attack=host_attack,stop=host_stop},clock=host_clock,
 profile={detect_radius=10,attack_radius=2,lose_radius=20,attack_cooldown=3},
 policy={allowed_kinds={character=true},blocked_kinds={vehicle=true},required_traits={human=true}}}))
return system:add_actor('actor')");
            Check((bool)result[0] && log.Count==0,"passive wiring or registration");
            Check(ActionOf(host.Execute("return system:tick()")[0])=="move","expected move");
            Check(log.Count==1 && log[0]=="move_to:actor:npc","vehicle rejected / exact movement identity");
            distance=1;
            Check(ActionOf(host.Execute("return system:tick()")[0])=="attack","expected attack");
            Check(log[1]=="attack:actor:npc","exact attack identity");
            Check(ActionOf(host.Execute("return system:tick()")[0])=="wait" && log.Count==2,"cooldown");
            now+=3;
            Check(ActionOf(host.Execute("return system:tick()")[0])=="attack" && log.Count==3,"cooldown expiry");
            alive=false;
            Check(ActionOf(host.Execute("return system:tick()")[0])=="lost","death loss");
            Check(log[3]=="stop:actor:","stop wrong actor; observed="+log[3]);
            result=host.Execute("return system:add_actor('actor')");
            Check(result[0]==null && (string)result[1]=="already_registered","nil/reason marshalling");
            Check((bool)host.Execute("return system:remove_actor('actor')")[0],"remove failed");
            Check(log.Count==5 && log[4]=="stop:actor:","remove stop identity");
            Check(((Dictionary<object,object>)host.Execute("return system:tick()")[0]).Count==0,"actor not removed");
            Console.WriteLine("MANAGED_GAMEPLAY_BRIDGE_OK vehicle_rejection move attack cooldown death_loss registration");
        }
    }
    private static void Boundaries() {
        using (var host=Small("return {value=42}")) {
            object[] denied=host.Execute("return os,io,package,debug,load,loadfile,dofile,_G,luanet");
            Check(denied.Length==9 && Array.TrueForAll(denied,x=>x==null),"ambient host access exposed");
            object[] values=host.Execute("return utf8.len('é'),7//2,require('probe')==require('probe'),require('probe').value");
            Check((double)values[0]==1 && (double)values[1]==3 && (bool)values[2] && (double)values[3]==42,"Lua54/cache");
            Exception wrong=null; var thread=new Thread(delegate(){try {host.Execute("return true");}catch(Exception e){wrong=e;}});
            thread.Start(); thread.Join(); Check(wrong!=null && wrong.Message.Contains("wrong_host_thread"),"thread ownership");
            for (int i=0;i<100;i++) Check((double)host.Execute("return 1")[0]==1,"stack leaked");
        }
        var sources=new Dictionary<string,string>{{"probe","return {value=1}"}};
        using (var host=new LuaModuleHost(sources)) {
            sources["probe"]="return {value=2}";
            Check((double)host.Execute("return require('probe').value")[0]==1,"source snapshot changed");
        }
        Failure(delegate { using(var h=new LuaModuleHost(new Dictionary<string,string>{{"../bad","return {}"}})){} },"module_identity_invalid");
        Failure(delegate { using(var h=Small(new String(' ',131073))){} },"module_size_invalid");
        Failure(delegate { using(var h=Small("return {}",999)){} },"host_limits_invalid");
        var disposed=Small(); disposed.Dispose(); Failure(delegate {disposed.Execute("return true");},"disposed");
        Console.WriteLine("MANAGED_HOST_BOUNDARIES_OK");
    }
    private static void Failures() {
        foreach (string code in new [] {"return require('../bad')","return require('missing')"})
            using(var h=Small()) { Failure(delegate {h.Execute(code);},"module_not_allowlisted"); Failure(delegate {h.Execute("return true");},"lua_host_faulted"); }
        using(var h=Small("return require('probe')")) Failure(delegate {h.Execute("return require('probe')");},"module_cycle");
        using(var h=Small("return function() end")) Failure(delegate {h.Execute("return require('probe')");},"module_must_return_table");
        using(var h=Small()) Failure(delegate {h.Execute("this is invalid lua!");},"operator");
        using(var h=Small(budget:5000)) Failure(delegate {h.Execute("while true do end");},"instruction_limit");
        using(var h=Small(budget:5000)) Failure(delegate {h.Execute("pcall(function() while true do end end); return true");},"instruction_limit");
        foreach (string code in new [] {"return function() end", "local t={};t.self=t;return t", "return 0/0"})
            using(var h=Small()) Failure(delegate {h.Execute(code);},"result_");
        using(var h=Small()) {
            h.SetCallback("host_throw",delegate(IntPtr p){throw new InvalidOperationException("provider_failed");});
            object[] result=h.Execute("return host_throw()");
            Check(result[0]==null && ((string)result[1]).Contains("provider_failed"),"callback error lost");
            Check((bool)h.Execute("return true")[0],"controlled refusal poisoned host");
        }
        using(var h=Small(callbackMs:5)) {
            h.SetCallback("host_slow",delegate(IntPtr p){Thread.Sleep(25); Lua.FromIntPtr(p).PushBoolean(true);return 1;});
            Failure(delegate {h.Execute("return host_slow()");},"lua_host_faulted");
            Failure(delegate {h.Execute("return true");},"lua_host_faulted");
        }
        Console.WriteLine("MANAGED_HOST_FAILURES_OK");
    }
    private static void Contracts(string root) {
        string[] names={"entity_policy_v1","predator_controller_v1","provider_admission_v1","predator_system_v1"};
        string[] subjects={"entity_policy","predator_controller","engine_adapter","raptor_system_main"};
        for(int i=0;i<names.Length;i++) using(var lua=new Lua()) {
            lua.Encoding=Encoding.UTF8;
            lua.GetGlobal("_VERSION"); Check(lua.ToString(-1)=="Lua 5.4","wrong Lua for frozen contract"); lua.SetTop(0);
            // Preserve the verifier's exit semantics while running all four VMs:
            // zero returns to this harness; every nonzero exit raises failure.
            Check(lua.LoadString("os.exit=function(code) if code~=0 then error('acceptance_exit:'..tostring(code)) end end")==LuaStatus.OK,"exit harness load");
            Check(lua.PCall(0,0,0)==LuaStatus.OK,"exit harness setup");
            lua.NewTable(); lua.PushString(Path.Combine(root,"subjects",subjects[i]+".lua").Replace('\\','/'));lua.RawSetInteger(-2,1);lua.SetGlobal("arg");
            byte[] source=File.ReadAllBytes(Path.Combine(root,"contracts",names[i]+".lua"));
            Check(lua.LoadBuffer(source,"@"+names[i],"t")==LuaStatus.OK,"verifier load");
            LuaStatus result=lua.PCall(0,0,0);
            if(result!=LuaStatus.OK)throw new Exception(lua.ToString(-1));
        }
        Console.WriteLine("MANAGED_FROZEN_CONTRACTS_OK 128");
    }
    public static int Main(string[] args) {
        try {
            if(args[0]=="gameplay") Gameplay(args[1]);
            else if(args[0]=="boundaries") Boundaries();
            else if(args[0]=="failures") Failures();
            else if(args[0]=="contracts") Contracts(args[1]);
            else throw new Exception("unknown fixture mode");
            return 0;
        }catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
}
