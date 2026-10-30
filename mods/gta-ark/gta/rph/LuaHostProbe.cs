// Operator-owned read-only diagnostic: the managed Lua 5.4 host inside the RPH process.
// Every player read goes through a Lua module and one read-only host callback.
// No spawning, movement, combat, memory patching or asset loading.
using System;
using KeraLua;
using Rage;
using Smelter.RuntimeProbe;

[assembly: Rage.Attributes.Plugin("SMELTER Lua Host Probe", Author = "SMELTER",
    Description = "Read-only managed Lua 5.4 host and game-fiber scheduling probe", PrefersSingleInstance = true)]

public static class EntryPoint
{
    public static void Main()
    {
        ProbeProfile profile = GtaProbeProfile.Create();
        profile.ReportChannel = "gta-rph-lua-host-probe";
        string receipt;
        using (var probe = new LuaTickProbe(PlayerRead))
        {
            receipt = ProbeHarness.Run(profile, probe.Tick, IsNetworkSessionActive, Sleep, typeof(Game).Assembly.FullName);
            probe.WriteEvidence(receipt);
        }
        Game.LogTrivial("[SMELTER] Lua host probe receipt: " + receipt);
    }

    // The only host callback: a read of the local player.
    private static int PlayerRead(IntPtr pointer)
    {
        Lua lua = Lua.FromIntPtr(pointer);
        Ped ped = Game.LocalPlayer.Character;
        if (ped == null || !ped.IsValid()) { lua.PushNil(); lua.PushString("player_ped_unavailable"); return 2; }
        Vector3 p = ped.Position;
        lua.PushString(ped.Handle.ToString()); lua.PushNumber(p.X); lua.PushNumber(p.Y); lua.PushNumber(p.Z);
        lua.PushBoolean(ped.IsHuman); lua.PushBoolean(!ped.IsDead);
        return 6;
    }

    private static bool IsNetworkSessionActive()
    {
        return Rage.Native.NativeFunction.Natives.NETWORK_IS_SESSION_ACTIVE<bool>();
    }

    private static void Sleep(int milliseconds)
    {
        GameFiber.Sleep(milliseconds);
    }
}
