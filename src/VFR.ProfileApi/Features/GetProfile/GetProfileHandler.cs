using MediatR;
using Microsoft.EntityFrameworkCore;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.Features.GetProfile;

public class GetProfileHandler(ProfileDbContext dbContext) : IRequestHandler<GetProfileQuery, GetProfileResponse?>
{
    public async Task<GetProfileResponse?> Handle(GetProfileQuery request, CancellationToken cancellationToken)
    {
        var profile = await dbContext.PhysicalProfiles
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.UserId == request.UserId, cancellationToken);

        if (profile is null) return null;

        return new GetProfileResponse
        {
            Id = profile.Id,
            UserId = profile.UserId,
            Height = (double)profile.Height,
            Weight = (double)profile.Weight,
            BodyType = profile.BodyType.ToString()
        };
    }
}
