// Engine-neutral Lua host probe: one reviewed in-memory module reads the player through a
// single read-only host callback on every tick. No game API, filesystem loader or command.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Threading;
using KeraLua;
using Smelter.ManagedLua;

namespace Smelter.RuntimeProbe
{
    [DataContract]
    public sealed class LuaHostEvidence
    {
        [DataMember(Name="schema_version")] public int SchemaVersion = 1;
        [DataMember(Name="lua_version")] public string LuaVersion;
        [DataMember(Name="lua54_module_path")] public string Lua54Path;
        [DataMember(Name="lua54_sha256")] public string Lua54Sha256;
        [DataMember(Name="keralua_path")] public string KeraLuaPath;
        [DataMember(Name="keralua_sha256")] public string KeraLuaSha256;
        [DataMember(Name="host_thread_id")] public int HostThreadId;
        [DataMember(Name="tick_thread_ids")] public List<int> TickThreadIds = new List<int>();
        [DataMember(Name="tick_numbers")] public List<int> TickNumbers = new List<int>();
        [DataMember(Name="integer_division")] public bool IntegerDivision = true;
        [DataMember(Name="integer_subtype")] public bool IntegerSubtype = true;
        [DataMember(Name="utf8_library")] public bool Utf8Library = true;
        [DataMember(Name="ambient_libraries_absent")] public bool AmbientLibrariesAbsent;
        [DataMember(Name="callback_calls")] public int CallbackCalls;
        [DataMember(Name="host_mutating_callbacks")] public int MutatingCallbacks;
    }

    public sealed class LuaTickProbe : IDisposable
    {
        // Reviewed in-memory module; the host never reads Lua from disk.
        public const string Module = @"
local probe = {}
function probe.tick(n)
  local handle, x, y, z, human, alive = host_player()
  if handle == nil then return nil, x end
  return {handle=handle, x=x, y=y, z=z, human=human, alive=alive, n=n,
          idiv=7//2, int=math.type(n), utf8=utf8.char(0x41, 0x3A9)}
end
return probe
";
        public readonly LuaHostEvidence Evidence = new LuaHostEvidence();
        private readonly LuaFunction playerRead;
        private LuaModuleHost host;
        private int tick;

        // playerRead must take no Lua arguments and return handle, x, y, z, human, alive
        // (or nil, reason). It is the only callback, so the probe cannot issue a command.
        public LuaTickProbe(LuaFunction playerRead)
        {
            if (playerRead == null) throw new ArgumentNullException("playerRead");
            this.playerRead = playerRead;
        }

        private void Start()
        {
            host = new LuaModuleHost(new Dictionary<string,string> { { "probe_tick", Module } });
            Evidence.LuaVersion = host.Version;
            Evidence.HostThreadId = Thread.CurrentThread.ManagedThreadId;
            host.SetCallback("host_player", delegate(IntPtr pointer) {
                Evidence.CallbackCalls++;
                if (Lua.FromIntPtr(pointer).GetTop() != 0) throw new InvalidOperationException("host_player_takes_no_arguments");
                return playerRead(pointer);
            });
            object[] ambient = host.Execute("return os == nil and io == nil and package == nil and debug == nil and load == nil", "ambient");
            Evidence.AmbientLibrariesAbsent = ambient.Length == 1 && Equals(ambient[0], true);
            Evidence.KeraLuaPath = typeof(Lua).Assembly.Location;
            Evidence.KeraLuaSha256 = ProbeHarness.HashFile(Evidence.KeraLuaPath);
            using (Process process = Process.GetCurrentProcess())
                foreach (ProcessModule module in process.Modules)
                    if (String.Equals(module.ModuleName, "lua54.dll", StringComparison.OrdinalIgnoreCase))
                    { Evidence.Lua54Path = module.FileName; Evidence.Lua54Sha256 = ProbeHarness.HashFile(module.FileName); }
            if (Evidence.Lua54Path == null) throw new InvalidOperationException("lua54_module_not_found");
        }

        // One read through Lua. The harness checks identity and network state before each call.
        public NativeReadSample Tick()
        {
            if (host == null) Start();
            tick++;
            Evidence.TickNumbers.Add(tick);
            Evidence.TickThreadIds.Add(Thread.CurrentThread.ManagedThreadId);
            object[] result = host.Execute("return require('probe_tick').tick(" + tick + ")", "tick");
            var row = result.Length > 0 ? result[0] as Dictionary<object,object> : null;
            if (row == null) throw new InvalidOperationException("lua_tick_failed:" + (result.Length > 1 ? result[1] : "no_result"));
            if (!Equals(row["idiv"], 3.0)) Evidence.IntegerDivision = false;
            if (!Equals(row["int"], "integer")) Evidence.IntegerSubtype = false;
            if (!Equals(row["utf8"], "AΩ")) Evidence.Utf8Library = false;
            return new NativeReadSample {
                Handle = row["handle"] as string, Valid = true, Human = Equals(row["human"], true), Alive = Equals(row["alive"], true),
                X = Convert.ToDouble(row["x"]), Y = Convert.ToDouble(row["y"]), Z = Convert.ToDouble(row["z"])
            };
        }

        // Written beside the harness report; skipped when the harness produced none.
        public void WriteEvidence(string receipt)
        {
            if (receipt == null) return;
            string path = Path.Combine(Path.GetDirectoryName(receipt), "lua_host.json");
            using (FileStream stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                new DataContractJsonSerializer(typeof(LuaHostEvidence)).WriteObject(stream, Evidence);
        }

        public void Dispose()
        {
            if (host != null) { host.Dispose(); host = null; }
        }
    }
}
