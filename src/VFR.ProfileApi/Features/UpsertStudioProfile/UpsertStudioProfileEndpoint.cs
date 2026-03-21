using FluentValidation;
using MediatR;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Mvc;
using VFR.ProfileApi.Features.GetProfile;

namespace VFR.ProfileApi.Features.UpsertStudioProfile;

public static class UpsertStudioProfileEndpoint
{
    public static IEndpointRouteBuilder MapUpsertStudioProfile(this IEndpointRouteBuilder routes)
    {
        routes.MapPut("/me/studio", HandleAsync)
              .RequireAuthorization()
              .WithName("UpsertStudioProfile")
              .WithSummary("Creates or replaces the current Studio body state for the authenticated user.")
              .Produces<GetProfileResponse>(StatusCodes.Status200OK)
              .ProducesProblem(StatusCodes.Status400BadRequest)
              .ProducesProblem(StatusCodes.Status401Unauthorized);

        return routes;
    }

    private static async Task<Results<Ok<GetProfileResponse>, ValidationProblem>> HandleAsync(
        [FromBody] UpsertStudioProfileRequest request,
        IValidator<UpsertStudioProfileCommand> validator,
        ISender sender,
        HttpContext httpContext,
        CancellationToken ct)
    {
        var userId = httpContext.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                     ?? string.Empty;

        var command = new UpsertStudioProfileCommand(
            userId,
            request.Height,
            request.Weight,
            request.BodyType,
            request.Gender,
            request.Muscularity,
            request.BodyFatPercentage,
            request.ChestCircumference,
            request.WaistCircumference,
            request.HipCircumference,
            request.ShoulderWidth,
            request.CalfCircumference,
            request.ArmLength,
            request.TorsoLength,
            request.LegLength,
            request.AutoChestCircumference,
            request.AutoWaistCircumference,
            request.AutoHipCircumference,
            request.AutoArmLength,
            request.AutoLegLength,
            request.GeneratedAvatar is null
                ? null
                : new UpsertStudioGeneratedAvatarCommand(
                    request.GeneratedAvatar.ModelUrl,
                    request.GeneratedAvatar.GeneratedAt));

        var validation = await validator.ValidateAsync(command, ct);
        if (!validation.IsValid)
            return TypedResults.ValidationProblem(validation.ToDictionary());

        var result = await sender.Send(command, ct);
        return TypedResults.Ok(result);
    }
}
