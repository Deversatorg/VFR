using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;

internal static class DatabaseBootstrapControl
{
    internal const string SkipStartupDatabaseBootstrapKey = "VFR_DISABLE_STARTUP_DB_BOOTSTRAP";
    internal const string EnableStartupDatabaseBootstrapKey = "VFR_ENABLE_STARTUP_DB_BOOTSTRAP";

    internal static bool ShouldSkip(IConfiguration configuration, IHostEnvironment environment)
    {
        if (environment.IsProduction())
        {
            // In Production, bootstrap should NOT run by default.
            // Explicit opt-in is required to prevent concurrent migration issues.
            return !configuration.GetValue<bool>(EnableStartupDatabaseBootstrapKey);
        }

        // In Development/Testing, run by default unless explicitly disabled
        return configuration.GetValue<bool>(SkipStartupDatabaseBootstrapKey);
    }
}
