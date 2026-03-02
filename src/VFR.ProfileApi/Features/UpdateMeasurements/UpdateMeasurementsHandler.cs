using MediatR;
using Microsoft.EntityFrameworkCore;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.UpdateMeasurements;

public sealed class UpdateMeasurementsHandler(
    ProfileDbContext db
) : IRequestHandler<UpdateMeasurementsCommand, UpdateMeasurementsResult>
{
    public async Task<UpdateMeasurementsResult> Handle(UpdateMeasurementsCommand cmd, CancellationToken ct)
    {
        var profile = await db.PhysicalProfiles
            .FirstOrDefaultAsync(p => p.UserId == cmd.UserId, ct)
            ?? throw new KeyNotFoundException($"No profile found for user {cmd.UserId}. Run quick-setup first.");

        if (cmd.ChestCircumference.HasValue) profile.ChestCircumference = cmd.ChestCircumference;
        if (cmd.WaistCircumference.HasValue) profile.WaistCircumference = cmd.WaistCircumference;
        if (cmd.HipCircumference.HasValue)   profile.HipCircumference   = cmd.HipCircumference;
        if (cmd.ShoulderWidth.HasValue)       profile.ShoulderWidth       = cmd.ShoulderWidth;

        profile.UpdatedAt = DateTime.UtcNow;

        await db.SaveChangesAsync(ct);

        return new UpdateMeasurementsResult(
            profile.Id,
            profile.ChestCircumference,
            profile.WaistCircumference,
            profile.HipCircumference,
            profile.ShoulderWidth
        );
    }
}
