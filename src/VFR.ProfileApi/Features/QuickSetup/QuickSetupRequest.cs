using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Features.QuickSetup;

/// <summary>Request DTO for the quick-setup endpoint.</summary>
public sealed record QuickSetupRequest(
    decimal  Height,
    decimal  Weight,
    BodyType BodyType
);
