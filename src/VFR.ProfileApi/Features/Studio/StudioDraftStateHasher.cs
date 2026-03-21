using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Features.Studio;

public static class StudioDraftStateHasher
{
    public static string Compute(PhysicalProfile profile) =>
        Compute(
            profile.Height,
            profile.Weight,
            profile.BodyType,
            profile.Gender,
            profile.Muscularity,
            profile.BodyFatPercentage,
            profile.ChestCircumference,
            profile.WaistCircumference,
            profile.HipCircumference,
            profile.ShoulderWidth,
            profile.CalfCircumference,
            profile.ArmLength,
            profile.TorsoLength,
            profile.LegLength);

    public static string Compute(
        decimal height,
        decimal weight,
        BodyType bodyType,
        AvatarGender gender,
        decimal? muscularity,
        decimal? bodyFatPercentage,
        decimal? chestCircumference,
        decimal? waistCircumference,
        decimal? hipCircumference,
        decimal? shoulderWidth,
        decimal? calfCircumference,
        decimal? armLength,
        decimal? torsoLength,
        decimal? legLength)
    {
        var normalized = string.Join(
            "|",
            Format(height),
            Format(weight),
            bodyType.ToString().ToLowerInvariant(),
            gender.ToString().ToLowerInvariant(),
            Format(muscularity),
            Format(bodyFatPercentage),
            Format(chestCircumference),
            Format(waistCircumference),
            Format(hipCircumference),
            Format(shoulderWidth),
            Format(calfCircumference),
            Format(armLength),
            Format(torsoLength),
            Format(legLength));

        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(normalized));
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static string Format(decimal value) =>
        value.ToString("0.##", CultureInfo.InvariantCulture);

    private static string Format(decimal? value) =>
        value.HasValue ? Format(value.Value) : "-";
}
