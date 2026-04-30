using MediatR;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.GetProfile;

namespace VFR.ProfileApi.Features.UpsertStudioProfile;

public sealed record UpsertStudioProfileCommand(
    string UserId,
    decimal Height,
    decimal Weight,
    BodyType BodyType,
    AvatarGender Gender,
    decimal? Muscularity,
    decimal? BodyFatPercentage,
    decimal? ChestCircumference,
    decimal? WaistCircumference,
    decimal? HipCircumference,
    decimal? ShoulderWidth,
    decimal? CalfCircumference,
    decimal? ArmLength,
    decimal? TorsoLength,
    decimal? LegLength,
    decimal? AutoChestCircumference,
    decimal? AutoWaistCircumference,
    decimal? AutoHipCircumference,
    decimal? AutoArmLength,
    decimal? AutoLegLength
) : IRequest<GetProfileResponse>;
