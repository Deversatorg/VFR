namespace VFR.ProfileApi.IntegrationTests;

internal static class TestHostDefaults
{
    internal const string JwtIssuer = "ApplicationAuthAuthServer";
    internal const string JwtAudience = "Client";
    internal const string JwtSigningKey = "integration-tests-signing-key-1234567890";

    internal static Dictionary<string, string?> Configuration { get; } = new()
    {
        ["VFR_DISABLE_STARTUP_DB_BOOTSTRAP"] = "true",
        ["Jwt:Issuer"] = JwtIssuer,
        ["Jwt:Audience"] = JwtAudience,
        ["Jwt:SigningKey"] = JwtSigningKey,
    };
}
