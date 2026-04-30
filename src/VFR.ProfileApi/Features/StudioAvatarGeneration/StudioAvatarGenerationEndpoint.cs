using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.GetProfile;
using VFR.ProfileApi.Features.Studio;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.StudioAvatarGeneration;

public static class StudioAvatarGenerationEndpoint
{
    public static IEndpointRouteBuilder MapStudioAvatarGeneration(this IEndpointRouteBuilder routes)
    {
        routes.MapPost("/me/studio/avatar-generation", StartAsync)
            .RequireAuthorization()
            .WithName("StartStudioAvatarGeneration")
            .WithSummary("Queues avatar generation for the authenticated user's saved Studio profile.")
            .Produces<StudioAvatarGenerationStartResponse>(StatusCodes.Status200OK)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status502BadGateway);

        routes.MapGet("/me/studio/avatar-generation/{taskId}", GetStatusAsync)
            .RequireAuthorization()
            .WithName("GetStudioAvatarGenerationStatus")
            .WithSummary("Gets avatar generation status and persists the generated avatar metadata on success.")
            .Produces<StudioAvatarGenerationStatusResponse>(StatusCodes.Status200OK)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status502BadGateway);

        return routes;
    }

    private static async Task<IResult> StartAsync(
        ClaimsPrincipal user,
        ProfileDbContext db,
        IAiEngineClient aiEngine,
        IStudioAvatarGenerationTracker tracker,
        CancellationToken ct)
    {
        var userId = GetUserId(user);
        if (string.IsNullOrWhiteSpace(userId))
        {
            return Results.Unauthorized();
        }

        var profile = await db.PhysicalProfiles.FirstOrDefaultAsync(p => p.UserId == userId, ct);
        if (profile is null)
        {
            return Results.NotFound(new { Detail = "Studio profile not found for current user." });
        }

        try
        {
            var accepted = await aiEngine.EnqueueProfileAvatarAsync(profile, ct);
            var draftHash = StudioDraftStateHasher.Compute(profile);
            await tracker.RegisterAsync(new StudioAvatarGenerationTask(
                accepted.TaskId,
                userId,
                draftHash,
                DateTime.UtcNow),
                ct);

            return Results.Ok(new StudioAvatarGenerationStartResponse(
                accepted.TaskId,
                accepted.Status,
                accepted.Message));
        }
        catch (Exception ex) when (ex is InvalidOperationException or HttpRequestException)
        {
            return Results.Problem(
                title: "Avatar generation unavailable",
                detail: ex.Message,
                statusCode: StatusCodes.Status502BadGateway);
        }
    }

    private static async Task<IResult> GetStatusAsync(
        string taskId,
        ClaimsPrincipal user,
        ProfileDbContext db,
        IAiEngineClient aiEngine,
        IStudioAvatarGenerationTracker tracker,
        CancellationToken ct)
    {
        var userId = GetUserId(user);
        if (string.IsNullOrWhiteSpace(userId))
        {
            return Results.Unauthorized();
        }

        var trackedTask = await tracker.GetAsync(taskId, ct);
        if (trackedTask is null ||
            !string.Equals(trackedTask.UserId, userId, StringComparison.Ordinal))
        {
            return Results.NotFound(new { Detail = "Avatar generation task not found for current user." });
        }

        AiAvatarStatusResponse aiStatus;
        try
        {
            aiStatus = await aiEngine.GetAvatarStatusAsync(taskId, ct);
        }
        catch (Exception ex) when (ex is InvalidOperationException or HttpRequestException)
        {
            return Results.Problem(
                title: "Avatar generation status unavailable",
                detail: ex.Message,
                statusCode: StatusCodes.Status502BadGateway);
        }

        var status = NormalizeStatus(aiStatus.Status);
        var progress = Math.Clamp(aiStatus.Progress ?? 0, 0, 100);
        var message = aiStatus.Message ?? string.Empty;

        if (status is not "SUCCESS")
        {
            return Results.Ok(new StudioAvatarGenerationStatusResponse(
                taskId,
                status,
                progress,
                message,
                Result: null));
        }

        var modelUrl = aiEngine.NormalizeModelUrl(aiStatus.Result?.ModelUrl);
        if (string.IsNullOrWhiteSpace(modelUrl))
        {
            return Results.Ok(new StudioAvatarGenerationStatusResponse(
                taskId,
                "FAILURE",
                0,
                "AI generation completed without a fetchable model_url.",
                Result: null));
        }

        var profile = await db.PhysicalProfiles.FirstOrDefaultAsync(p => p.UserId == userId, ct);
        if (profile is null)
        {
            return Results.NotFound(new { Detail = "Studio profile not found for current user." });
        }

        var currentDraftHash = StudioDraftStateHasher.Compute(profile);
        if (!string.Equals(currentDraftHash, trackedTask.DraftStateHash, StringComparison.Ordinal))
        {
            return Results.Ok(new StudioAvatarGenerationStatusResponse(
                taskId,
                "STALE",
                100,
                "Studio draft changed while generation was running. Generate again for the current body.",
                Result: null));
        }

        if (string.Equals(profile.LastAvatarInputHash, trackedTask.DraftStateHash, StringComparison.Ordinal) &&
            string.Equals(profile.LastAvatarModelUrl, modelUrl, StringComparison.Ordinal))
        {
            return Results.Ok(new StudioAvatarGenerationStatusResponse(
                taskId,
                "SUCCESS",
                100,
                "Completed",
                CreateResult(modelUrl, aiStatus, profile)));
        }

        profile.LastAvatarModelUrl = modelUrl;
        profile.LastAvatarGeneratedAt = DateTime.UtcNow;
        profile.LastAvatarInputHash = trackedTask.DraftStateHash;
        ApplyAutoMeasurements(profile, aiStatus.Result?.Measurements);
        profile.UpdatedAt = DateTime.UtcNow;

        await db.SaveChangesAsync(ct);

        return Results.Ok(new StudioAvatarGenerationStatusResponse(
            taskId,
            "SUCCESS",
            100,
            "Completed",
            CreateResult(modelUrl, aiStatus, profile)));
    }

    private static string GetUserId(ClaimsPrincipal user) =>
        user.FindFirst(ClaimTypes.NameIdentifier)?.Value
        ?? user.FindFirst("sub")?.Value
        ?? string.Empty;

    private static string NormalizeStatus(string? status) =>
        string.IsNullOrWhiteSpace(status)
            ? "UNKNOWN"
            : status.Trim().ToUpperInvariant();

    private static void ApplyAutoMeasurements(
        PhysicalProfile profile,
        IReadOnlyDictionary<string, double>? measurements)
    {
        if (measurements is null)
        {
            return;
        }

        profile.AutoChestCircumference = ToPositiveDecimal(measurements, "chest_cm") ?? profile.AutoChestCircumference;
        profile.AutoWaistCircumference = ToPositiveDecimal(measurements, "waist_cm") ?? profile.AutoWaistCircumference;
        profile.AutoHipCircumference = ToPositiveDecimal(measurements, "hips_cm") ?? profile.AutoHipCircumference;
        profile.AutoArmLength = ToPositiveDecimal(measurements, "arm_length_cm") ?? profile.AutoArmLength;
        profile.AutoLegLength = ToPositiveDecimal(measurements, "leg_length_cm") ?? profile.AutoLegLength;
    }

    private static decimal? ToPositiveDecimal(IReadOnlyDictionary<string, double> values, string key)
    {
        if (!values.TryGetValue(key, out var value) || value <= 0)
        {
            return null;
        }

        return Convert.ToDecimal(value);
    }

    private static StudioAvatarGenerationResultResponse CreateResult(
        string modelUrl,
        AiAvatarStatusResponse aiStatus,
        PhysicalProfile profile)
    {
        var profileResponse = GetProfileResponse.FromProfile(profile);
        return new StudioAvatarGenerationResultResponse(
            modelUrl,
            aiStatus.Result?.Measurements ?? new Dictionary<string, double>(),
            aiStatus.Result?.Targets ?? new Dictionary<string, double>(),
            aiStatus.Result?.MeasurementSources ?? new Dictionary<string, string>(),
            profileResponse);
    }
}

public sealed record StudioAvatarGenerationStartResponse(
    string TaskId,
    string Status,
    string Message
);

public sealed record StudioAvatarGenerationStatusResponse(
    string TaskId,
    string Status,
    int Progress,
    string Message,
    StudioAvatarGenerationResultResponse? Result
);

public sealed record StudioAvatarGenerationResultResponse(
    string ModelUrl,
    Dictionary<string, double> Measurements,
    Dictionary<string, double> Targets,
    Dictionary<string, string> MeasurementSources,
    GetProfileResponse Profile
);
