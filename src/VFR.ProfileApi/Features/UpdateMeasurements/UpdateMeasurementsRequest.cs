namespace VFR.ProfileApi.Features.UpdateMeasurements;

/// <summary>Request DTO for the measurements patch endpoint.</summary>
public sealed record UpdateMeasurementsRequest(
    decimal? ChestCircumference,
    decimal? WaistCircumference,
    decimal? HipCircumference,
    decimal? ShoulderWidth
);
