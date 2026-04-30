using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Features.StudioAvatarGeneration;

public interface IAiEngineClient
{
    Task<AiAvatarGenerationAcceptedResponse> EnqueueProfileAvatarAsync(PhysicalProfile profile, CancellationToken ct);
    Task<AiAvatarStatusResponse> GetAvatarStatusAsync(string taskId, CancellationToken ct);
    string? NormalizeModelUrl(string? modelUrl);
}

public sealed class AiEngineClient(
    HttpClient httpClient,
    IConfiguration configuration,
    ILogger<AiEngineClient> logger
) : IAiEngineClient
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private readonly Uri? baseAddress = ResolveBaseAddress(configuration);
    private readonly Uri? publicBaseAddress = ResolvePublicBaseAddress(configuration) ?? ResolveBaseAddress(configuration);

    public async Task<AiAvatarGenerationAcceptedResponse> EnqueueProfileAvatarAsync(
        PhysicalProfile profile,
        CancellationToken ct)
    {
        EnsureConfigured();

        var request = new AiProfileAvatarRequest(
            UserId: profile.UserId,
            Height: (double)profile.Height,
            Weight: (double)profile.Weight,
            BodyType: profile.BodyType.ToString().ToLowerInvariant(),
            Gender: profile.Gender.ToString().ToLowerInvariant(),
            Muscularity: ToDouble(profile.Muscularity),
            BodyFatPercentage: ToDouble(profile.BodyFatPercentage),
            Chest: ToDouble(profile.ChestCircumference),
            Waist: ToDouble(profile.WaistCircumference),
            Hip: ToDouble(profile.HipCircumference),
            Shoulder: ToDouble(profile.ShoulderWidth),
            Calf: ToDouble(profile.CalfCircumference),
            ArmLength: ToDouble(profile.ArmLength),
            TorsoLength: ToDouble(profile.TorsoLength),
            LegLength: ToDouble(profile.LegLength),
            FaceImageUrl: string.Empty);

        using var response = await httpClient.PostAsJsonAsync(
            "/api/v1/avatar/generate-from-profile",
            request,
            JsonOptions,
            ct);

        if (!response.IsSuccessStatusCode)
        {
            var body = await response.Content.ReadAsStringAsync(ct);
            logger.LogWarning(
                "AI engine avatar enqueue failed with status {StatusCode}: {Body}",
                (int)response.StatusCode,
                body);
            throw new HttpRequestException(
                $"AI engine enqueue failed with status {(int)response.StatusCode}.");
        }

        var payload = await response.Content.ReadFromJsonAsync<AiAvatarGenerationAcceptedResponse>(JsonOptions, ct);
        if (payload is null || string.IsNullOrWhiteSpace(payload.TaskId))
        {
            throw new InvalidOperationException("AI engine returned an empty avatar enqueue response.");
        }

        return payload;
    }

    public async Task<AiAvatarStatusResponse> GetAvatarStatusAsync(string taskId, CancellationToken ct)
    {
        EnsureConfigured();

        using var response = await httpClient.GetAsync(
            $"/api/v1/avatar/status/{Uri.EscapeDataString(taskId)}",
            ct);

        if (!response.IsSuccessStatusCode)
        {
            var body = await response.Content.ReadAsStringAsync(ct);
            logger.LogWarning(
                "AI engine avatar status failed with status {StatusCode}: {Body}",
                (int)response.StatusCode,
                body);
            throw new HttpRequestException(
                $"AI engine status failed with status {(int)response.StatusCode}.");
        }

        var payload = await response.Content.ReadFromJsonAsync<AiAvatarStatusResponse>(JsonOptions, ct);

        return payload ?? throw new InvalidOperationException("AI engine returned an empty avatar status response.");
    }

    public string? NormalizeModelUrl(string? modelUrl)
    {
        var value = modelUrl?.Trim();
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        if (Uri.TryCreate(value, UriKind.Absolute, out var absolute) &&
            (absolute.Scheme == Uri.UriSchemeHttp || absolute.Scheme == Uri.UriSchemeHttps))
        {
            return absolute.ToString();
        }

        if (value.StartsWith("/models/", StringComparison.Ordinal) && publicBaseAddress is not null)
        {
            return new Uri(publicBaseAddress, value).ToString();
        }

        return null;
    }

    private void EnsureConfigured()
    {
        if (baseAddress is null)
        {
            throw new InvalidOperationException("AiEngine:BaseUrl is not configured.");
        }

        httpClient.BaseAddress ??= baseAddress;
    }

    private static Uri? ResolveBaseAddress(IConfiguration configuration)
    {
        var raw = configuration["AiEngine:BaseUrl"]?.Trim()
            ?? configuration["AI_ENGINE_BASE_URL"]?.Trim();

        if (string.IsNullOrWhiteSpace(raw))
        {
            return null;
        }

        if (!raw.EndsWith("/", StringComparison.Ordinal))
        {
            raw += "/";
        }

        return Uri.TryCreate(raw, UriKind.Absolute, out var uri) ? uri : null;
    }

    private static Uri? ResolvePublicBaseAddress(IConfiguration configuration)
    {
        var raw = configuration["AiEngine:PublicBaseUrl"]?.Trim()
            ?? configuration["AI_ENGINE_PUBLIC_BASE_URL"]?.Trim();

        if (string.IsNullOrWhiteSpace(raw))
        {
            return null;
        }

        if (!raw.EndsWith("/", StringComparison.Ordinal))
        {
            raw += "/";
        }

        return Uri.TryCreate(raw, UriKind.Absolute, out var uri) ? uri : null;
    }

    private static double ToDouble(decimal? value) => value.HasValue ? (double)value.Value : 0d;
}

public sealed record AiProfileAvatarRequest(
    [property: JsonPropertyName("user_id")] string UserId,
    [property: JsonPropertyName("height")] double Height,
    [property: JsonPropertyName("weight")] double Weight,
    [property: JsonPropertyName("body_type")] string BodyType,
    [property: JsonPropertyName("gender")] string Gender,
    [property: JsonPropertyName("muscularity")] double Muscularity,
    [property: JsonPropertyName("body_fat_percentage")] double BodyFatPercentage,
    [property: JsonPropertyName("chest")] double Chest,
    [property: JsonPropertyName("waist")] double Waist,
    [property: JsonPropertyName("hip")] double Hip,
    [property: JsonPropertyName("shoulder")] double Shoulder,
    [property: JsonPropertyName("calf")] double Calf,
    [property: JsonPropertyName("arm_length")] double ArmLength,
    [property: JsonPropertyName("torso_length")] double TorsoLength,
    [property: JsonPropertyName("leg_length")] double LegLength,
    [property: JsonPropertyName("face_image_url")] string FaceImageUrl
);

public sealed record AiAvatarGenerationAcceptedResponse(
    [property: JsonPropertyName("task_id")] string TaskId,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("message")] string Message
);

public sealed record AiAvatarStatusResponse(
    [property: JsonPropertyName("task_id")] string? TaskId,
    [property: JsonPropertyName("status")] string? Status,
    [property: JsonPropertyName("progress")] int? Progress,
    [property: JsonPropertyName("message")] string? Message,
    [property: JsonPropertyName("result")] AiAvatarStatusResult? Result
);

public sealed record AiAvatarStatusResult(
    [property: JsonPropertyName("model_url")] string? ModelUrl,
    [property: JsonPropertyName("measurements")] Dictionary<string, double>? Measurements,
    [property: JsonPropertyName("targets")] Dictionary<string, double>? Targets,
    [property: JsonPropertyName("measurement_sources")] Dictionary<string, string>? MeasurementSources
);
