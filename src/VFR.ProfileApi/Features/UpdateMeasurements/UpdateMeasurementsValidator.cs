using FluentValidation;

namespace VFR.ProfileApi.Features.UpdateMeasurements;

public sealed class UpdateMeasurementsValidator : AbstractValidator<UpdateMeasurementsCommand>
{
    public UpdateMeasurementsValidator()
    {
        RuleFor(x => x.UserId)
            .NotEmpty().WithMessage("UserId is required.");

        When(x => x.ChestCircumference.HasValue, () =>
            RuleFor(x => x.ChestCircumference!.Value)
                .InclusiveBetween(30, 200)
                .WithMessage("ChestCircumference must be between 30 and 200 cm."));

        When(x => x.WaistCircumference.HasValue, () =>
            RuleFor(x => x.WaistCircumference!.Value)
                .InclusiveBetween(30, 200)
                .WithMessage("WaistCircumference must be between 30 and 200 cm."));

        When(x => x.HipCircumference.HasValue, () =>
            RuleFor(x => x.HipCircumference!.Value)
                .InclusiveBetween(30, 200)
                .WithMessage("HipCircumference must be between 30 and 200 cm."));

        When(x => x.ShoulderWidth.HasValue, () =>
            RuleFor(x => x.ShoulderWidth!.Value)
                .InclusiveBetween(20, 100)
                .WithMessage("ShoulderWidth must be between 20 and 100 cm."));
    }
}
