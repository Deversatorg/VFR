using MediatR;
using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Features.QuickSetup;

/// <summary>
/// Command: create or overwrite the user's basic profile.
/// </summary>
public sealed record QuickSetupCommand(
    string   UserId,
    decimal  Height,
    decimal  Weight,
    BodyType BodyType
) : IRequest<QuickSetupResult>;

public sealed record QuickSetupResult(
    Guid   ProfileId,
    string AvatarModelUrl
);
