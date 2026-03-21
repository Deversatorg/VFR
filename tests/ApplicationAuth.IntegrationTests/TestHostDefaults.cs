using ApplicationAuth.Common.Constants;

namespace ApplicationAuth.IntegrationTests;

internal static class TestHostDefaults
{
    internal const string JwtSigningKey = "integration-tests-signing-key-1234567890";

    internal static Dictionary<string, string?> Configuration { get; } = new()
    {
        ["VFR_DISABLE_STARTUP_DB_BOOTSTRAP"] = "true",
        ["Jwt:Issuer"] = AuthOptions.DefaultIssuer,
        ["Jwt:Audience"] = AuthOptions.DefaultAudience,
        ["Jwt:SigningKey"] = JwtSigningKey,
    };
}
