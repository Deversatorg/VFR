using FluentValidation;
using MediatR;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Mvc;

namespace VFR.ProfileApi.Features.QuickSetup;

public static class QuickSetupEndpoint
{
    public static IEndpointRouteBuilder MapQuickSetup(this IEndpointRouteBuilder routes)
    {
        routes.MapPost("/quick-setup", HandleAsync)
              .RequireAuthorization()
              .WithName("QuickSetup")
              .WithSummary("Creates or replaces the user's basic body profile.")
              .Produces<QuickSetupResult>(StatusCodes.Status200OK)
              .ProducesProblem(StatusCodes.Status400BadRequest)
              .ProducesProblem(StatusCodes.Status401Unauthorized);

        return routes;
    }

    private static async Task<Results<Ok<QuickSetupResult>, ValidationProblem>> HandleAsync(
        [FromBody]                 QuickSetupRequest       request,
        IValidator<QuickSetupCommand>                      validator,
        ISender                                            sender,
        HttpContext                                        httpContext,
        CancellationToken                                  ct)
    {
        var userId = httpContext.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                     ?? string.Empty;

        var command = new QuickSetupCommand(userId, request.Height, request.Weight, request.BodyType);

        var validation = await validator.ValidateAsync(command, ct);
        if (!validation.IsValid)
            return TypedResults.ValidationProblem(validation.ToDictionary());

        var result = await sender.Send(command, ct);
        return TypedResults.Ok(result);
    }
}
