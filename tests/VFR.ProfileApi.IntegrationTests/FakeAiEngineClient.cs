using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.StudioAvatarGeneration;

namespace VFR.ProfileApi.IntegrationTests;

public sealed class FakeAiEngineClient : IAiEngineClient
{
    public PhysicalProfile? LastProfile { get; private set; }

    public Task<AiAvatarGenerationAcceptedResponse> EnqueueProfileAvatarAsync(
        PhysicalProfile profile,
        CancellationToken ct)
    {
        LastProfile = profile;
        return Task.FromResult(new AiAvatarGenerationAcceptedResponse(
            TaskId: "queued-profile-avatar",
            Status: "accepted",
            Message: "Parametric avatar generation task queued."));
    }

    public Task<AiAvatarStatusResponse> GetAvatarStatusAsync(string taskId, CancellationToken ct) =>
        Task.FromResult(new AiAvatarStatusResponse(
            TaskId: taskId,
            Status: "SUCCESS",
            Progress: 100,
            Message: "Completed",
            Result: new AiAvatarStatusResult(
                ModelUrl: "/models/generated-avatar.glb",
                Measurements: new Dictionary<string, double>
                {
                    ["chest_cm"] = 102,
                    ["waist_cm"] = 84,
                    ["hips_cm"] = 99,
                    ["arm_length_cm"] = 63,
                    ["leg_length_cm"] = 109,
                },
                Targets: new Dictionary<string, double>
                {
                    ["chest_cm"] = 101,
                    ["waist_cm"] = 83,
                },
                MeasurementSources: new Dictionary<string, string>
                {
                    ["chest_cm"] = "user",
                    ["waist_cm"] = "user",
                })));

    public string? NormalizeModelUrl(string? modelUrl)
    {
        if (string.IsNullOrWhiteSpace(modelUrl))
        {
            return null;
        }

        return modelUrl.StartsWith("/models/", StringComparison.Ordinal)
            ? $"http://ai.test{modelUrl}"
            : modelUrl;
    }
}
