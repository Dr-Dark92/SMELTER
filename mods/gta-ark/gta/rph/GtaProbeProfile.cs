using Smelter.RuntimeProbe;

public static class GtaProbeProfile
{
    public static ProbeProfile Create()
    {
        return new ProbeProfile {
            ExecutableName = "GTA5_Enhanced.exe", ExecutableVersion = "1.0.1158.16",
            ExecutableSha256 = "b48e80f5fc899eb89e5dcc9f3b68e9551cc8dcfac78b2a940b207e569e9987ea", ReportChannel = "gta-rph-read-probe",
            SampleCount = 4, DelayMilliseconds = 250
        };
    }
}
