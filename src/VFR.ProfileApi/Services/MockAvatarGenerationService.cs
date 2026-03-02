using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Services;

/// <summary>
/// Mock implementation — returns a static placeholder .glb URL.
/// Replace with a gRPC client in Phase 3.
/// </summary>
public sealed class MockAvatarGenerationService : IAvatarGenerationService
{
    public Task<string> GetAvatarModelUrlAsync(PhysicalProfile profile, CancellationToken ct = default)
    {
        // TODO Phase 3: call VFR.AiEngine via gRPC with profile parameters
        var stub = $"https://storage.vfr.dev/models/base_{profile.BodyType.ToString().ToLowerInvariant()}.glb";
        return Task.FromResult(stub);
    }
}
