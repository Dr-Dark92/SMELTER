// Operator-reviewed test executable. No RPH reference, game API or real game access.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using Smelter.RuntimeProbe;

[assembly: AssemblyFileVersion("1.0.0.0")]

public static class RuntimeProbeFixture
{
    public static int Main(string[] args)
    {
        string scenario = args[0];
        string exe = Process.GetCurrentProcess().MainModule.FileName;
        var profile = new ProbeProfile {
            ExecutableName = Path.GetFileName(exe),
            ExecutableVersion = FileVersionInfo.GetVersionInfo(exe).FileVersion,
            ExecutableSha256 = ProbeHarness.HashFile(exe),
            ReportChannel = "fixture", SampleCount = 4, DelayMilliseconds = 0
        };
        if (scenario == "wrong_hash") profile.ExecutableSha256 = new String('0', 64);
        if (scenario == "wrong_name") profile.ExecutableName = "other.exe";
        if (scenario == "wrong_version") profile.ExecutableVersion = "0.0.0.0";
        if (scenario == "sample_limit") profile.SampleCount = 11;
        if (scenario == "delay_limit") profile.DelayMilliseconds = 1001;
        if (scenario == "channel_escape") profile.ReportChannel = "../escape";
        int reads = 0, checks = 0, pauses = 0;
        string receipt = ProbeHarness.Run(profile,
            delegate {
                reads++;
                if (scenario == "capture_throws") throw new InvalidOperationException("capture_failed");
                if (scenario == "missing_sample") return null;
                return new NativeReadSample {
                    Handle = "fake-ped-1", Valid = scenario != "invalid_sample", Human = true, Alive = true,
                    X = scenario == "nan_position" ? Double.NaN : 1,
                    Y = scenario == "infinite_position" ? Double.PositiveInfinity : 2, Z = 3
                };
            },
            delegate {
                checks++;
                if (scenario == "network_throws") throw new InvalidOperationException("network_unknown");
                return scenario == "network_active" || (scenario == "network_changes" && checks == 2);
            },
            delegate(int delay) {
                pauses++;
                if (scenario == "pause_throws") throw new InvalidOperationException("scheduler_failed");
            },
            "fake-runtime-no-game", args[1]);
        Console.WriteLine(receipt);
        Console.WriteLine(reads + "," + checks + "," + pauses);
        return 0;
    }
}
