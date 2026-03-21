using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Features.UpsertStudioProfile;

public sealed record UpsertStudioGeneratedAvatarRequest(
    string ModelUrl,
    DateTime? GeneratedAt
);

public sealed record UpsertStudioProfileRequest(
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
    decimal? AutoLegLength,
    UpsertStudioGeneratedAvatarRequest? GeneratedAvatar
);
