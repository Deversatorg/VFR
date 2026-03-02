using System.Net.Http.Json;

namespace VFR.Web.Services;

public record QuickSetupRequest(decimal Height, decimal Weight, string BodyType);
public record UpdateMeasurementsRequest(
    decimal? ChestCircumference,
    decimal? WaistCircumference,
    decimal? HipCircumference,
    decimal? ShoulderWidth);

public record ProfileResponse(
    Guid Id,
    string UserId,
    decimal Height,
    decimal Weight,
    string BodyType,
    decimal? ChestCircumference,
    decimal? WaistCircumference,
    decimal? HipCircumference,
    decimal? ShoulderWidth,
    string? AvatarUrl);

/// <summary>
/// Typed HTTP client for VFR.ProfileApi — attaches the JWT Bearer token
/// from AuthService to every request automatically.
/// </summary>
public class ProfileApiClient
{
    private readonly HttpClient _http;
    private readonly AuthService _auth;

    public ProfileApiClient(HttpClient http, AuthService auth)
    {
        _http = http;
        _auth = auth;
    }

    private void AddAuth()
    {
        var bearer = _auth.GetBearerHeader();
        _http.DefaultRequestHeaders.Remove("Authorization");
        if (bearer != null)
            _http.DefaultRequestHeaders.TryAddWithoutValidation("Authorization", bearer);
    }

    public async Task<(ProfileResponse? Profile, string? Error)> QuickSetupAsync(
        decimal height, decimal weight, string bodyType)
    {
        AddAuth();
        var response = await _http.PostAsJsonAsync("/api/profile/quick-setup",
            new QuickSetupRequest(height, weight, bodyType));

        if (!response.IsSuccessStatusCode)
            return (null, await response.Content.ReadAsStringAsync());

        var profile = await response.Content.ReadFromJsonAsync<ProfileResponse>();
        return (profile, null);
    }

    public async Task<(ProfileResponse? Profile, string? Error)> UpdateMeasurementsAsync(
        decimal? chest, decimal? waist, decimal? hip, decimal? shoulder)
    {
        AddAuth();
        var response = await _http.PatchAsJsonAsync("/api/profile/measurements",
            new UpdateMeasurementsRequest(chest, waist, hip, shoulder));

        if (!response.IsSuccessStatusCode)
            return (null, await response.Content.ReadAsStringAsync());

        var profile = await response.Content.ReadFromJsonAsync<ProfileResponse>();
        return (profile, null);
    }
}
