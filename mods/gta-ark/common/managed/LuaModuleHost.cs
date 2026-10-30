// Engine-neutral, operator-owned Lua 5.4 bridge. No game API or filesystem loader.
// Reviewed code only: this in-process interpreter is not a security boundary.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using KeraLua;

namespace Smelter.ManagedLua
{
    public sealed class LuaModuleHost : IDisposable
    {
        private readonly Lua state;
        private readonly int ownerThread = Thread.CurrentThread.ManagedThreadId;
        private readonly List<LuaFunction> retained = new List<LuaFunction>();
        private readonly int runReference, bindingReference, instructionBudget, callbackMilliseconds;
        private bool disposed, running, faulted;
        public string Version { get; private set; }

        // Private upvalues hold the compiler/hook. Loaded modules receive only env.
        // The pure-Lua hook errors inside native protected execution, never across
        // a managed hook callback. It does not preempt a blocking CLR callback.
        private const string Bootstrap = @"
local sources, bindings, cache, loading = __sources, {}, {}, {}
__sources = nil
local compile, hook, pack, unpack = load, debug.sethook, table.pack, table.unpack
local env = {}
for _, k in ipairs({'assert','error','ipairs','next','pairs','pcall','select',
 'tonumber','tostring','type','xpcall','setmetatable','getmetatable','rawget','rawset','rawequal'}) do
 env[k] = _G[k]
end
for _, k in ipairs({'math','string','table','utf8'}) do
 env[k] = {}; for n, f in pairs(_G[k]) do env[k][n] = f end
end
setmetatable(env, {__index=bindings, __metatable=false})
env.require = function(name)
 if type(name) ~= 'string' or sources[name] == nil then error('module_not_allowlisted', 0) end
 if cache[name] ~= nil then return cache[name] end
 if loading[name] then error('module_cycle', 0) end
 loading[name] = true
 local fn, err = compile(sources[name], '@' .. name, 't', env)
 if not fn then error(err, 0) end
 local value = fn()
 if type(value) ~= 'table' then error('module_must_return_table', 0) end
 cache[name], loading[name] = value, nil
 return value
end
local function run(source, label, budget)
 local fn, err = compile(source, '@' .. label, 't', env)
 if not fn then return false, err end
 local exhausted = false
 hook(function() exhausted=true; error('instruction_limit',0) end, '', budget)
 local out = pack(pcall(fn))
 hook()
 if exhausted then return false, 'instruction_limit' end
 if not out[1] then return false, tostring(out[2]) end
 local values = {n=out.n-1}; for i=2,out.n do values[i-1]=out[i] end
 return true, values
end
return {run=run, bindings=bindings}
";

        public LuaModuleHost(IDictionary<string,string> sources, int instructionBudget = 200000,
            int callbackMilliseconds = 100)
        {
            if (sources == null || sources.Count < 1 || sources.Count > 16)
                throw new ArgumentException("module_count_invalid");
            if (instructionBudget < 1000 || instructionBudget > 1000000 || callbackMilliseconds < 1 || callbackMilliseconds > 1000)
                throw new ArgumentException("host_limits_invalid");
            int bytes = 0;
            foreach (var entry in sources)
            {
                if (entry.Key == null || entry.Key.Length > 100 || !Regex.IsMatch(entry.Key, @"\A[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\z"))
                    throw new ArgumentException("module_identity_invalid");
                int size = entry.Value == null ? -1 : Encoding.UTF8.GetByteCount(entry.Value);
                if (size < 0 || size > 131072) throw new ArgumentException("module_size_invalid");
                bytes += size;
            }
            if (bytes > 1048576) throw new ArgumentException("module_total_size_invalid");
            this.instructionBudget = instructionBudget; this.callbackMilliseconds = callbackMilliseconds;
            state = new Lua(); state.Encoding = Encoding.UTF8;
            try
            {
                state.GetGlobal("_VERSION"); Version = state.ToString(-1); state.SetTop(0);
                if (Version != "Lua 5.4") throw new InvalidOperationException("unsupported_lua_version:" + Version);
                state.NewTable();
                foreach (var entry in sources) { state.PushString(entry.Value); state.SetField(-2, entry.Key); }
                state.SetGlobal("__sources");
                Check(state.LoadBuffer(Encoding.UTF8.GetBytes(Bootstrap), "@smelter-host", "t"));
                Check(state.PCall(0, 1, 0));
                state.GetField(-1, "run"); runReference = state.Ref(LuaRegistry.Index);
                state.GetField(-1, "bindings"); bindingReference = state.Ref(LuaRegistry.Index);
                state.SetTop(0);
                // None of these are in the module env. Also remove root access paths.
                foreach (string name in new [] { "os", "io", "package", "debug", "loadfile", "dofile", "load", "require" })
                { state.PushNil(); state.SetGlobal(name); }
            }
            catch { state.Dispose(); throw; }
        }

        private void Check(LuaStatus status)
        {
            if (status != LuaStatus.OK) throw new InvalidOperationException(state.ToString(-1) ?? "lua_execution_failed");
        }

        private void Available()
        {
            if (Thread.CurrentThread.ManagedThreadId != ownerThread) throw new InvalidOperationException("wrong_host_thread");
            if (disposed) throw new ObjectDisposedException("LuaModuleHost");
            if (faulted) throw new InvalidOperationException("lua_host_faulted");
            if (running) throw new InvalidOperationException("lua_host_reentry");
        }

        // The engine adapter supplies bounded callbacks; only explicit Lua values
        // cross this API. No CLR reflection/object translator is registered.
        public void SetCallback(string name, LuaFunction callback)
        {
            Available();
            if (name == null || !Regex.IsMatch(name, @"\Ahost_[a-z][a-z0-9_]*\z") || name.Length > 100 || callback == null)
                throw new ArgumentException("callback_identity_invalid");
            if (retained.Count >= 32) throw new InvalidOperationException("callback_limit");
            LuaFunction wrapped = delegate(IntPtr pointer) {
                Lua current = Lua.FromIntPtr(pointer); Stopwatch timer = Stopwatch.StartNew();
                try
                {
                    int count = callback(pointer);
                    if (count < 0 || count > 16 || count > current.GetTop()) throw new InvalidOperationException("callback_result_count_invalid");
                    if (timer.ElapsedMilliseconds > callbackMilliseconds) {
                        faulted = true; throw new InvalidOperationException("callback_time_limit");
                    }
                    return count;
                }
                catch (Exception error) {
                    current.PushNil(); current.PushString("host_callback_error:" + error.GetType().Name + ":" + error.Message);
                    return 2;
                }
            };
            retained.Add(wrapped); retained.Add(callback);
            state.RawGetInteger(LuaRegistry.Index, bindingReference);
            state.PushCFunction(wrapped); state.SetField(-2, name); state.SetTop(0);
        }

        public object[] Execute(string source, string label = "operator", int? budget = null)
        {
            Available();
            if (source == null || Encoding.UTF8.GetByteCount(source) > 131072 || label == null || label.Length > 100)
                throw new ArgumentException("chunk_identity_or_size_invalid");
            int limit = budget ?? instructionBudget;
            if (limit < 1000 || limit > instructionBudget) throw new ArgumentException("chunk_budget_invalid");
            running = true;
            try
            {
                state.RawGetInteger(LuaRegistry.Index, runReference);
                state.PushString(source); state.PushString(label); state.PushInteger(limit);
                Check(state.PCall(3, 2, 0));
                if (faulted) throw new InvalidOperationException("lua_host_faulted");
                if (!state.ToBoolean(-2)) throw new InvalidOperationException(state.ToString(-1) ?? "lua_chunk_failed");
                int valuesIndex = state.GetTop();
                state.GetField(valuesIndex, "n"); long count = state.ToInteger(-1); state.SetTop(valuesIndex);
                if (count < 0 || count > 16) throw new InvalidOperationException("result_count_invalid");
                var result = new object[(int)count]; int nodes = 0;
                for (int i = 0; i < result.Length; i++) {
                    state.RawGetInteger(valuesIndex, i + 1);
                    result[i] = Read(-1, 0, new HashSet<IntPtr>(), ref nodes); state.SetTop(valuesIndex);
                }
                return result;
            }
            catch { faulted = true; throw; }
            finally { state.SetTop(0); running = false; }
        }

        private object Read(int index, int depth, HashSet<IntPtr> seen, ref int nodes)
        {
            if (++nodes > 4096 || depth > 16) throw new InvalidOperationException("result_size_limit");
            switch (state.Type(index))
            {
                case LuaType.Nil: return null;
                case LuaType.Boolean: return state.ToBoolean(index);
                case LuaType.String:
                    string text = state.ToString(index);
                    if (Encoding.UTF8.GetByteCount(text) > 65536) throw new InvalidOperationException("result_string_limit");
                    return text;
                case LuaType.Number:
                    double number = state.ToNumber(index);
                    if (Double.IsNaN(number) || Double.IsInfinity(number)) throw new InvalidOperationException("result_nonfinite");
                    return number;
                case LuaType.Table:
                    IntPtr identity = state.ToPointer(index);
                    if (!seen.Add(identity)) throw new InvalidOperationException("result_cycle");
                    int absolute = index > 0 ? index : state.GetTop() + index + 1;
                    var table = new Dictionary<object,object>(); state.PushNil();
                    while (state.Next(absolute)) {
                        LuaType keyType = state.Type(-2);
                        if (keyType != LuaType.String && keyType != LuaType.Number) throw new InvalidOperationException("result_key_invalid");
                        object key = Read(-2, depth+1, seen, ref nodes);
                        table.Add(key, Read(-1, depth+1, seen, ref nodes)); state.SetTop(state.GetTop()-1);
                    }
                    seen.Remove(identity); return table;
                default: throw new InvalidOperationException("result_type_unsupported");
            }
        }

        public void Dispose()
        {
            if (Thread.CurrentThread.ManagedThreadId != ownerThread) throw new InvalidOperationException("wrong_host_thread");
            if (running) throw new InvalidOperationException("lua_host_reentry");
            if (!disposed) { disposed = true; state.Dispose(); retained.Clear(); }
        }
    }
}
