using MediatR;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.GetProfile;
using VFR.ProfileApi.Features.Studio;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.UpsertStudioProfile;

public sealed class UpsertStudioProfileHandler(
    ProfileDbContext db,
    ILogger<UpsertStudioProfileHandler> logger
) : IRequestHandler<UpsertStudioProfileCommand, GetProfileResponse>
{
    public async Task<GetProfileResponse> Handle(UpsertStudioProfileCommand cmd, CancellationToken ct)
    {
        var profile = await db.PhysicalProfiles
            .FirstOrDefaultAsync(p => p.UserId == cmd.UserId, ct);
        var createdProfile = false;

        if (profile is null)
        {
            profile = new PhysicalProfile
            {
                UserId = cmd.UserId,
            };
            db.PhysicalProfiles.Add(profile);
            createdProfile = true;

            logger.LogInformation(
                "Creating Studio profile shell for user {UserId}.",
                cmd.UserId);
        }

        profile.Height = cmd.Height;
        profile.Weight = cmd.Weight;
        profile.BodyType = cmd.BodyType;
        profile.Gender = cmd.Gender;
        profile.Muscularity = cmd.Muscularity;
        profile.BodyFatPercentage = cmd.BodyFatPercentage;

        profile.ChestCircumference = cmd.ChestCircumference;
        profile.WaistCircumference = cmd.WaistCircumference;
        profile.HipCircumference = cmd.HipCircumference;
        profile.ShoulderWidth = cmd.ShoulderWidth;
        profile.CalfCircumference = cmd.CalfCircumference;
        profile.ArmLength = cmd.ArmLength;
        profile.TorsoLength = cmd.TorsoLength;
        profile.LegLength = cmd.LegLength;

        profile.AutoChestCircumference = cmd.AutoChestCircumference;
        profile.AutoWaistCircumference = cmd.AutoWaistCircumference;
        profile.AutoHipCircumference = cmd.AutoHipCircumference;
        profile.AutoArmLength = cmd.AutoArmLength;
        profile.AutoLegLength = cmd.AutoLegLength;

        profile.UpdatedAt = DateTime.UtcNow;

        await db.SaveChangesAsync(ct);

        logger.LogInformation(
            "Studio profile {Action} for user {UserId}. Height={Height}, Weight={Weight}.",
            createdProfile ? "created" : "updated",
            cmd.UserId,
            cmd.Height,
            cmd.Weight);

        return GetProfileResponse.FromProfile(profile);
    }
}
