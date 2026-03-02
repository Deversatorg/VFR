using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Services;

/// <summary>
/// Abstraction over the AI avatar generation service.
/// In Phase 3 this will be a gRPC client pointing to VFR.AiEngine.
/// </summary>
public interface IAvatarGenerationService
{
    Task<string> GetAvatarModelUrlAsync(PhysicalProfile profile, CancellationToken ct = default);
}
