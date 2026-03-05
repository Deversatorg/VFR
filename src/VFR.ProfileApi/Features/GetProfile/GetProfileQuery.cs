using MediatR;

namespace VFR.ProfileApi.Features.GetProfile;

public record GetProfileQuery(string UserId) : IRequest<GetProfileResponse?>;
