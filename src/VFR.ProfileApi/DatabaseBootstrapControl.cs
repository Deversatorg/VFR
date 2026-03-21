using Microsoft.Extensions.Configuration;

internal static class DatabaseBootstrapControl
{
    internal const string SkipStartupDatabaseBootstrapKey = "VFR_DISABLE_STARTUP_DB_BOOTSTRAP";

    internal static bool ShouldSkip(IConfiguration configuration) =>
        configuration.GetValue<bool>(SkipStartupDatabaseBootstrapKey);
}
