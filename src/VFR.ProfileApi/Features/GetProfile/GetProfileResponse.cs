using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.Studio;

namespace VFR.ProfileApi.Features.GetProfile;

public class GetProfileResponse
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public double Height { get; set; }
    public double Weight { get; set; }
    public string BodyType { get; set; } = string.Empty;
    public string Gender { get; set; } = string.Empty;
    public double? Muscularity { get; set; }
    public double? BodyFatPercentage { get; set; }
    public string DraftStateHash { get; set; } = string.Empty;
    public string? LastAvatarModelUrl { get; set; }
    public ProfileGeneratedAvatarResponse GeneratedAvatar { get; set; } = new();
    public ProfileManualMeasurementsResponse ManualMeasurements { get; set; } = new();
    public ProfileAutoMeasurementsResponse AutoMeasurements { get; set; } = new();

    public static GetProfileResponse FromProfile(PhysicalProfile profile)
    {
        var draftStateHash = StudioDraftStateHasher.Compute(profile);
        var generatedAvatarModelUrl = string.IsNullOrWhiteSpace(profile.LastAvatarModelUrl)
            ? null
            : profile.LastAvatarModelUrl;

        return new GetProfileResponse
        {
            Id = profile.Id,
            UserId = profile.UserId,
            Height = (double)profile.Height,
            Weight = (double)profile.Weight,
            BodyType = profile.BodyType.ToString(),
            Gender = profile.Gender.ToString(),
            Muscularity = ToNullableDouble(profile.Muscularity),
            BodyFatPercentage = ToNullableDouble(profile.BodyFatPercentage),
            DraftStateHash = draftStateHash,
            LastAvatarModelUrl = generatedAvatarModelUrl,
            GeneratedAvatar = new ProfileGeneratedAvatarResponse
            {
                ModelUrl = generatedAvatarModelUrl,
                GeneratedAt = profile.LastAvatarGeneratedAt,
                InputHash = profile.LastAvatarInputHash,
                IsCurrent =
                    generatedAvatarModelUrl is not null &&
                    !string.IsNullOrWhiteSpace(profile.LastAvatarInputHash) &&
                    string.Equals(profile.LastAvatarInputHash, draftStateHash, StringComparison.Ordinal)
            },
            ManualMeasurements = new ProfileManualMeasurementsResponse
            {
                ChestCircumference = ToNullableDouble(profile.ChestCircumference),
                WaistCircumference = ToNullableDouble(profile.WaistCircumference),
                HipCircumference = ToNullableDouble(profile.HipCircumference),
                ShoulderWidth = ToNullableDouble(profile.ShoulderWidth),
                CalfCircumference = ToNullableDouble(profile.CalfCircumference),
                ArmLength = ToNullableDouble(profile.ArmLength),
                TorsoLength = ToNullableDouble(profile.TorsoLength),
                LegLength = ToNullableDouble(profile.LegLength),
            },
            AutoMeasurements = new ProfileAutoMeasurementsResponse
            {
                ChestCircumference = ToNullableDouble(profile.AutoChestCircumference),
                WaistCircumference = ToNullableDouble(profile.AutoWaistCircumference),
                HipCircumference = ToNullableDouble(profile.AutoHipCircumference),
                ArmLength = ToNullableDouble(profile.AutoArmLength),
                LegLength = ToNullableDouble(profile.AutoLegLength),
            }
        };
    }

    private static double? ToNullableDouble(decimal? value) => value.HasValue ? (double)value.Value : null;
}

public class ProfileManualMeasurementsResponse
{
    public double? ChestCircumference { get; set; }
    public double? WaistCircumference { get; set; }
    public double? HipCircumference { get; set; }
    public double? ShoulderWidth { get; set; }
    public double? CalfCircumference { get; set; }
    public double? ArmLength { get; set; }
    public double? TorsoLength { get; set; }
    public double? LegLength { get; set; }
}

public class ProfileGeneratedAvatarResponse
{
    public string? ModelUrl { get; set; }
    public DateTime? GeneratedAt { get; set; }
    public string? InputHash { get; set; }
    public bool IsCurrent { get; set; }
}

public class ProfileAutoMeasurementsResponse
{
    public double? ChestCircumference { get; set; }
    public double? WaistCircumference { get; set; }
    public double? HipCircumference { get; set; }
    public double? ArmLength { get; set; }
    public double? LegLength { get; set; }
}
