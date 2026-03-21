using FluentValidation;

namespace VFR.ProfileApi.Features.UpsertStudioProfile;

public sealed class UpsertStudioProfileValidator : AbstractValidator<UpsertStudioProfileCommand>
{
    public UpsertStudioProfileValidator()
    {
        RuleFor(x => x.UserId)
            .NotEmpty().WithMessage("UserId is required.");

        RuleFor(x => x.Height)
            .InclusiveBetween(100, 250)
            .WithMessage("Height must be between 100 and 250 cm.");

        RuleFor(x => x.Weight)
            .InclusiveBetween(30, 300)
            .WithMessage("Weight must be between 30 and 300 kg.");

        When(x => x.Muscularity.HasValue, () =>
            RuleFor(x => x.Muscularity!.Value)
                .InclusiveBetween(0, 100)
                .WithMessage("Muscularity must be between 0 and 100."));

        When(x => x.BodyFatPercentage.HasValue, () =>
            RuleFor(x => x.BodyFatPercentage!.Value)
                .InclusiveBetween(2, 70)
                .WithMessage("BodyFatPercentage must be between 2 and 70 percent."));

        When(x => x.GeneratedAvatar is not null, () =>
        {
            RuleFor(x => x.GeneratedAvatar!.ModelUrl)
                .NotEmpty()
                .WithMessage("GeneratedAvatar.ModelUrl is required when generated avatar metadata is provided.")
                .MaximumLength(2048)
                .WithMessage("GeneratedAvatar.ModelUrl must be 2048 characters or fewer.");
        });

        When(x => x.ChestCircumference.HasValue, () =>
            RuleFor(x => x.ChestCircumference!.Value)
                .InclusiveBetween(20, 260)
                .WithMessage("ChestCircumference must be between 20 and 260 cm."));

        When(x => x.WaistCircumference.HasValue, () =>
            RuleFor(x => x.WaistCircumference!.Value)
                .InclusiveBetween(20, 260)
                .WithMessage("WaistCircumference must be between 20 and 260 cm."));

        When(x => x.HipCircumference.HasValue, () =>
            RuleFor(x => x.HipCircumference!.Value)
                .InclusiveBetween(20, 260)
                .WithMessage("HipCircumference must be between 20 and 260 cm."));

        When(x => x.ShoulderWidth.HasValue, () =>
            RuleFor(x => x.ShoulderWidth!.Value)
                .InclusiveBetween(15, 160)
                .WithMessage("ShoulderWidth must be between 15 and 160 cm."));

        When(x => x.CalfCircumference.HasValue, () =>
            RuleFor(x => x.CalfCircumference!.Value)
                .InclusiveBetween(10, 100)
                .WithMessage("CalfCircumference must be between 10 and 100 cm."));

        When(x => x.ArmLength.HasValue, () =>
            RuleFor(x => x.ArmLength!.Value)
                .InclusiveBetween(20, 130)
                .WithMessage("ArmLength must be between 20 and 130 cm."));

        When(x => x.TorsoLength.HasValue, () =>
            RuleFor(x => x.TorsoLength!.Value)
                .InclusiveBetween(20, 140)
                .WithMessage("TorsoLength must be between 20 and 140 cm."));

        When(x => x.LegLength.HasValue, () =>
            RuleFor(x => x.LegLength!.Value)
                .InclusiveBetween(30, 170)
                .WithMessage("LegLength must be between 30 and 170 cm."));

        When(x => x.AutoChestCircumference.HasValue, () =>
            RuleFor(x => x.AutoChestCircumference!.Value)
                .InclusiveBetween(20, 260)
                .WithMessage("AutoChestCircumference must be between 20 and 260 cm."));

        When(x => x.AutoWaistCircumference.HasValue, () =>
            RuleFor(x => x.AutoWaistCircumference!.Value)
                .InclusiveBetween(20, 260)
                .WithMessage("AutoWaistCircumference must be between 20 and 260 cm."));

        When(x => x.AutoHipCircumference.HasValue, () =>
            RuleFor(x => x.AutoHipCircumference!.Value)
                .InclusiveBetween(20, 260)
                .WithMessage("AutoHipCircumference must be between 20 and 260 cm."));

        When(x => x.AutoArmLength.HasValue, () =>
            RuleFor(x => x.AutoArmLength!.Value)
                .InclusiveBetween(20, 130)
                .WithMessage("AutoArmLength must be between 20 and 130 cm."));

        When(x => x.AutoLegLength.HasValue, () =>
            RuleFor(x => x.AutoLegLength!.Value)
                .InclusiveBetween(30, 170)
                .WithMessage("AutoLegLength must be between 30 and 170 cm."));
    }
}
