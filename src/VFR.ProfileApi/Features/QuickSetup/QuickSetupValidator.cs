using FluentValidation;

namespace VFR.ProfileApi.Features.QuickSetup;

public sealed class QuickSetupValidator : AbstractValidator<QuickSetupCommand>
{
    public QuickSetupValidator()
    {
        RuleFor(x => x.UserId)
            .NotEmpty().WithMessage("UserId is required.");

        RuleFor(x => x.Height)
            .InclusiveBetween(50, 300)
            .WithMessage("Height must be between 50 and 300 cm.");

        RuleFor(x => x.Weight)
            .InclusiveBetween(20, 500)
            .WithMessage("Weight must be between 20 and 500 kg.");

        RuleFor(x => x.BodyType)
            .IsInEnum()
            .WithMessage("Invalid body type value.");
    }
}
