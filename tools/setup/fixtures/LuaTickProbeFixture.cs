// Reviewed offline driver for LuaTickProbe: fake player reads, real pinned Lua 5.4. No game.
using System;
using KeraLua;
using Smelter.RuntimeProbe;

public static class LuaTickProbeFixture
{
    public static int Main(string[] args)
    {
        string scenario = args[0];
        int reads = 0;
        LuaFunction read = delegate(IntPtr p) {
            Lua lua = Lua.FromIntPtr(p); reads++;
            if (scenario == "unavailable") { lua.PushNil(); lua.PushString("player_ped_unavailable"); return 2; }
            if (scenario == "throws") throw new InvalidOperationException("engine_read_failed");
            lua.PushString("fake-ped-7"); lua.PushNumber(1.5 * reads); lua.PushNumber(-2.25); lua.PushNumber(30);
            lua.PushBoolean(true); lua.PushBoolean(true); return 6;
        };
        using (var probe = new LuaTickProbe(read))
        {
            try
            {
                for (int i = 0; i < 4; i++)
                {
                    NativeReadSample s = probe.Tick(); s.Validate();
                    Console.WriteLine("SAMPLE|" + s.Handle + "|" + s.X + "|" + s.Y + "|" + s.Z + "|" + s.Human + "|" + s.Alive);
                }
            }
            catch (Exception error) { Console.WriteLine("ERROR|" + error.Message); }
            string folder = args[1]; System.IO.Directory.CreateDirectory(folder);
            probe.WriteEvidence(System.IO.Path.Combine(folder, "probe.json"));
        }
        return 0;
    }
}
