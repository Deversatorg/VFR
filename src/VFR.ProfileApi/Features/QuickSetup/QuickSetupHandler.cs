using MediatR;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.QuickSetup;

public sealed class QuickSetupHandler(
    ProfileDbContext db,
    ILogger<QuickSetupHandler> logger
) : IRequestHandler<QuickSetupCommand, QuickSetupResult>
{
    public async Task<QuickSetupResult> Handle(QuickSetupCommand cmd, CancellationToken ct)
    {
        var profile = await db.PhysicalProfiles
            .FirstOrDefaultAsync(p => p.UserId == cmd.UserId, ct);

        if (profile is null)
        {
            profile = new PhysicalProfile
            {
                UserId = cmd.UserId,
                Height = cmd.Height,
                Weight = cmd.Weight,
                BodyType = cmd.BodyType,
            };
            db.PhysicalProfiles.Add(profile);
            logger.LogInformation(
                "Quick setup created a new profile shell for user {UserId}.",
                cmd.UserId);
        }
        else
        {
            profile.Height = cmd.Height;
            profile.Weight = cmd.Weight;
            profile.BodyType = cmd.BodyType;
            profile.UpdatedAt = DateTime.UtcNow;
            logger.LogInformation(
                "Quick setup updated existing profile {ProfileId} for user {UserId}.",
                profile.Id,
                cmd.UserId);
        }

        await db.SaveChangesAsync(ct);

        logger.LogInformation(
            "Quick setup saved profile {ProfileId} for user {UserId}.",
            profile.Id,
            cmd.UserId);

        return new QuickSetupResult(profile.Id);
    }
}
