// Generic managed-host read probe instrumentation. No game API calls live here.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;

namespace Smelter.RuntimeProbe
{
    public sealed class ProbeProfile
    {
        public string ExecutableName;
        public string ExecutableVersion;
        public string ExecutableSha256;
        public string ReportChannel;
        public int SampleCount;
        public int DelayMilliseconds;
    }

    [DataContract]
    public sealed class NativeReadSample
    {
        [DataMember(Name="handle")] public string Handle;
        [DataMember(Name="valid")] public bool Valid;
        [DataMember(Name="human")] public bool Human;
        [DataMember(Name="alive")] public bool Alive;
        [DataMember(Name="x")] public double X;
        [DataMember(Name="y")] public double Y;
        [DataMember(Name="z")] public double Z;
        [DataMember(Name="utc")] public string Utc;

        public void Validate()
        {
            if (!Valid || String.IsNullOrWhiteSpace(Handle)) throw new InvalidOperationException("invalid_entity_sample");
            foreach (double n in new double[] { X, Y, Z })
                if (Double.IsNaN(n) || Double.IsInfinity(n)) throw new InvalidOperationException("nonfinite_position");
        }
    }

    [DataContract]
    public sealed class ProbeReport
    {
        [DataMember(Name="schema_version")] public int SchemaVersion;
        [DataMember(Name="stage")] public string Stage;
        [DataMember(Name="scope")] public string Scope;
        [DataMember(Name="run_id")] public string RunId;
        [DataMember(Name="process_id")] public int ProcessId;
        [DataMember(Name="executable")] public string Executable;
        [DataMember(Name="file_version")] public string FileVersion;
        [DataMember(Name="executable_sha256")] public string ExecutableSha256;
        [DataMember(Name="plugin_sha256")] public string PluginSha256;
        [DataMember(Name="runtime_assembly")] public string RuntimeAssembly;
        [DataMember(Name="network_session_checks")] public int NetworkSessionChecks;
        [DataMember(Name="native_reads_completed")] public bool NativeReadsCompleted;
        [DataMember(Name="game_runtime_verified")] public bool GameRuntimeVerified;
        [DataMember(Name="probe_mutating_calls")] public int ProbeMutatingCalls;
        [DataMember(Name="started_utc")] public string StartedUtc;
        [DataMember(Name="elapsed_ms")] public long ElapsedMilliseconds;
        [DataMember(Name="error")] public string Error;
        [DataMember(Name="samples")] public List<NativeReadSample> Samples;
    }

    public static class ProbeHarness
    {
        public static string HashFile(string path)
        {
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }

        public static string Run(ProbeProfile profile, Func<NativeReadSample> capture,
            Func<bool> networkSessionActive, Action<int> pause, string runtimeAssembly)
        {
            return Run(profile, capture, networkSessionActive, pause, runtimeAssembly, null);
        }

        // Tests compile this same harness with fake callbacks and an isolated output folder.
        // The shipped plugin calls only the public overload above.
        internal static string Run(ProbeProfile profile, Func<NativeReadSample> capture,
            Func<bool> networkSessionActive, Action<int> pause, string runtimeAssembly, string testOutputRoot)
        {
            var report = new ProbeReport {
                SchemaVersion = 1, Stage = "probe_failed", Scope = "read_only_native_probe_not_gameplay",
                RunId = Guid.NewGuid().ToString("N"), StartedUtc = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture),
                RuntimeAssembly = runtimeAssembly, Samples = new List<NativeReadSample>()
            };
            Stopwatch clock = Stopwatch.StartNew();
            string channel = "managed-read-probe";
            try
            {
                if (profile == null || capture == null || networkSessionActive == null || pause == null)
                    throw new InvalidOperationException("probe_dependencies_missing");
                if (profile.SampleCount < 1 || profile.SampleCount > 10 || profile.DelayMilliseconds < 0 || profile.DelayMilliseconds > 1000)
                    throw new InvalidOperationException("probe_limits_invalid");
                if (String.IsNullOrEmpty(profile.ReportChannel) || profile.ReportChannel.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 ||
                    profile.ReportChannel.Contains("..") || profile.ReportChannel.Contains("/") || profile.ReportChannel.Contains("\\"))
                    throw new InvalidOperationException("probe_channel_invalid");
                channel = profile.ReportChannel;
                using (Process process = Process.GetCurrentProcess())
                {
                    report.ProcessId = process.Id;
                    report.Executable = process.MainModule.FileName;
                    report.FileVersion = FileVersionInfo.GetVersionInfo(report.Executable).FileVersion;
                    report.ExecutableSha256 = HashFile(report.Executable);
                }
                if (!String.Equals(Path.GetFileName(report.Executable), profile.ExecutableName, StringComparison.OrdinalIgnoreCase) ||
                    !String.Equals(report.FileVersion, profile.ExecutableVersion, StringComparison.Ordinal) ||
                    !String.Equals(report.ExecutableSha256, profile.ExecutableSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("unsupported_executable_identity");
                string self = Assembly.GetExecutingAssembly().Location;
                if (String.IsNullOrEmpty(self) || !File.Exists(self)) throw new InvalidOperationException("plugin_identity_unavailable");
                report.PluginSha256 = HashFile(self);
                for (int i = 0; i < profile.SampleCount; i++)
                {
                    // Failure or uncertainty in this callback aborts before a player read.
                    report.NetworkSessionChecks++;
                    if (networkSessionActive()) throw new InvalidOperationException("network_session_active");
                    NativeReadSample sample = capture();
                    if (sample == null) throw new InvalidOperationException("sample_missing");
                    sample.Validate();
                    sample.Utc = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture);
                    report.Samples.Add(sample);
                    if (i + 1 < profile.SampleCount) pause(profile.DelayMilliseconds);
                }
                report.NativeReadsCompleted = true;
                report.Stage = "native_reads_observed";
                // This does not set GameRuntimeVerified: actions and Lua execution are separate gates.
            }
            catch (Exception error)
            {
                report.NativeReadsCompleted = false;
                report.Stage = "probe_failed";
                report.Error = error.GetType().Name + ":" + error.Message;
            }
            clock.Stop(); report.ElapsedMilliseconds = clock.ElapsedMilliseconds;
            string outputRoot = testOutputRoot;
            if (outputRoot == null)
            {
                string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (String.IsNullOrEmpty(local)) throw new IOException("LocalApplicationData_unavailable");
                outputRoot = Path.Combine(local, "SMELTER", "runtime-probes");
            }
            if (!Path.IsPathRooted(outputRoot)) throw new IOException("probe_output_root_not_absolute");
            string folder = Path.Combine(outputRoot, channel, report.RunId);
            Directory.CreateDirectory(folder);
            string path = Path.Combine(folder, "probe.json");
            using (FileStream stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                new DataContractJsonSerializer(typeof(ProbeReport)).WriteObject(stream, report);
            return path;
        }
    }
}
