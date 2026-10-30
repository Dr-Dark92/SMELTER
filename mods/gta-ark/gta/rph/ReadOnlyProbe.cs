// Operator-owned read-only diagnostic. No creature or gameplay actions.
using System;
using Rage;
using Smelter.RuntimeProbe;

[assembly: Rage.Attributes.Plugin("SMELTER Native Read Probe", Author = "SMELTER",
    Description = "Read-only native identity and player-position probe", PrefersSingleInstance = true)]

public static class EntryPoint
{
    public static void Main()
    {
        string receipt = ProbeHarness.Run(GtaProbeProfile.Create(), CaptureSample,
            IsNetworkSessionActive, Sleep, typeof(Game).Assembly.FullName);
        Game.LogTrivial("[SMELTER] Native read-probe receipt: " + receipt);
    }

    private static NativeReadSample CaptureSample()
    {
        Ped ped = Game.LocalPlayer.Character;
        if (ped == null || !ped.IsValid()) throw new InvalidOperationException("player_ped_unavailable");
        Vector3 position = ped.Position;
        return new NativeReadSample {
            Handle = ped.Handle.ToString(), Valid = true,
            Human = ped.IsHuman, Alive = !ped.IsDead,
            X = position.X, Y = position.Y, Z = position.Z
        };
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
