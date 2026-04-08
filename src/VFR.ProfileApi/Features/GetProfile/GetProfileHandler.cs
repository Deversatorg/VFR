using MediatR;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.GetProfile;

public class GetProfileHandler(
    ProfileDbContext dbContext,
    ILogger<GetProfileHandler> logger) : IRequestHandler<GetProfileQuery, GetProfileResponse?>
{
    public async Task<GetProfileResponse?> Handle(GetProfileQuery request, CancellationToken cancellationToken)
    {
        var profile = await dbContext.PhysicalProfiles
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.UserId == request.UserId, cancellationToken);

        if (profile is null)
        {
            logger.LogInformation("Profile lookup returned no record for user {UserId}.", request.UserId);
            return null;
        }

        logger.LogInformation(
            "Profile lookup returned profile {ProfileId} for user {UserId}.",
            profile.Id,
            request.UserId);

        return GetProfileResponse.FromProfile(profile);
    }
}
