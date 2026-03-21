using MediatR;
using Microsoft.EntityFrameworkCore;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.QuickSetup;

public sealed class QuickSetupHandler(
    ProfileDbContext db
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
                UserId   = cmd.UserId,
                Height   = cmd.Height,
                Weight   = cmd.Weight,
                BodyType = cmd.BodyType,
            };
            db.PhysicalProfiles.Add(profile);
        }
        else
        {
            profile.Height   = cmd.Height;
            profile.Weight   = cmd.Weight;
            profile.BodyType = cmd.BodyType;
            profile.UpdatedAt = DateTime.UtcNow;
        }

        await db.SaveChangesAsync(ct);

        return new QuickSetupResult(profile.Id);
    }
}
