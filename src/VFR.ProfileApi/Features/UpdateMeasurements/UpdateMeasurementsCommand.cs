using MediatR;
using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Features.UpdateMeasurements;

/// <summary>
/// Command: patch the detailed measurements on an existing profile.
/// </summary>
public sealed record UpdateMeasurementsCommand(
    string   UserId,
    decimal? ChestCircumference,
    decimal? WaistCircumference,
    decimal? HipCircumference,
    decimal? ShoulderWidth
) : IRequest<UpdateMeasurementsResult>;

public sealed record UpdateMeasurementsResult(
    Guid    ProfileId,
    decimal? Chest,
    decimal? Waist,
    decimal? Hip,
    decimal? Shoulder
);
