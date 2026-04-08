using MediatR;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.UpdateMeasurements;

public sealed class UpdateMeasurementsHandler(
    ProfileDbContext db,
    ILogger<UpdateMeasurementsHandler> logger
) : IRequestHandler<UpdateMeasurementsCommand, UpdateMeasurementsResult>
{
    public async Task<UpdateMeasurementsResult> Handle(UpdateMeasurementsCommand cmd, CancellationToken ct)
    {
        var profile = await db.PhysicalProfiles
            .FirstOrDefaultAsync(p => p.UserId == cmd.UserId, ct)
            ?? throw new KeyNotFoundException($"No profile found for user {cmd.UserId}. Run quick-setup first.");

        if (cmd.ChestCircumference.HasValue) profile.ChestCircumference = cmd.ChestCircumference;
        if (cmd.WaistCircumference.HasValue) profile.WaistCircumference = cmd.WaistCircumference;
        if (cmd.HipCircumference.HasValue) profile.HipCircumference = cmd.HipCircumference;
        if (cmd.ShoulderWidth.HasValue) profile.ShoulderWidth = cmd.ShoulderWidth;

        profile.UpdatedAt = DateTime.UtcNow;

        await db.SaveChangesAsync(ct);

        logger.LogInformation(
            "Updated measurements for profile {ProfileId} owned by user {UserId}. Fields updated: chest={HasChest}, waist={HasWaist}, hips={HasHips}, shoulder={HasShoulder}.",
            profile.Id,
            cmd.UserId,
            cmd.ChestCircumference.HasValue,
            cmd.WaistCircumference.HasValue,
            cmd.HipCircumference.HasValue,
            cmd.ShoulderWidth.HasValue);

        return new UpdateMeasurementsResult(
            profile.Id,
            profile.ChestCircumference,
            profile.WaistCircumference,
            profile.HipCircumference,
            profile.ShoulderWidth
        );
    }
}
