using Grpc.Net.Client;
using Microsoft.Extensions.Logging;
using VFR.Protos;
using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Services;

/// <summary>
/// Real implementation of IAvatarGenerationService that calls the VFR.AiEngine
/// Python gRPC sidecar to generate or update an avatar model URL.
/// Registered via Aspire service discovery — the channel address is resolved
/// from the "vfr-aiengine" service name injected by the AppHost.
/// </summary>
public sealed class GrpcAvatarGenerationService : IAvatarGenerationService
{
    private readonly AvatarService.AvatarServiceClient _client;
    private readonly ILogger<GrpcAvatarGenerationService> _logger;

    public GrpcAvatarGenerationService(
        AvatarService.AvatarServiceClient client,
        ILogger<GrpcAvatarGenerationService> logger)
    {
        _client = client;
        _logger  = logger;
    }

    public async Task<string> GetAvatarModelUrlAsync(
        PhysicalProfile profile,
        CancellationToken ct = default)
    {
        var request = new AvatarRequest
        {
            UserId    = profile.UserId,
            HeightCm  = (float)(profile.Height),
            WeightKg  = (float)(profile.Weight),
            BodyType  = profile.BodyType.ToString(),
            Chest     = (float)(profile.ChestCircumference ?? 0),
            Waist     = (float)(profile.WaistCircumference ?? 0),
            Hip       = (float)(profile.HipCircumference   ?? 0),
            Shoulder  = (float)(profile.ShoulderWidth      ?? 0),
        };

        _logger.LogInformation(
            "Calling AiEngine.GenerateAvatar for user {UserId} (BodyType={BodyType})",
            profile.UserId, profile.BodyType);

        try
        {
            var response = await _client.GenerateAvatarAsync(request, cancellationToken: ct);
            _logger.LogInformation("AiEngine returned avatar URL: {Url}", response.AvatarUrl);
            return response.AvatarUrl;
        }
        catch (Exception ex)
        {
            // Graceful degradation: return mock URL if AI engine is unavailable
            _logger.LogWarning(ex,
                "AiEngine gRPC call failed for user {UserId} — using fallback URL", profile.UserId);
            return $"https://storage.vfr.dev/models/fallback_{profile.BodyType.ToString().ToLower()}.glb";
        }
    }
}
