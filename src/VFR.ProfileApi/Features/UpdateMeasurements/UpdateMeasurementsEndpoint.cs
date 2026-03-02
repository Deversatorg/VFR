using FluentValidation;
using MediatR;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Mvc;

namespace VFR.ProfileApi.Features.UpdateMeasurements;

public static class UpdateMeasurementsEndpoint
{
    public static IEndpointRouteBuilder MapUpdateMeasurements(this IEndpointRouteBuilder routes)
    {
        routes.MapPatch("/measurements", HandleAsync)
              .RequireAuthorization()
              .WithName("UpdateMeasurements")
              .WithSummary("Partially updates the user's detailed body measurements.")
              .Produces<UpdateMeasurementsResult>(StatusCodes.Status200OK)
              .ProducesProblem(StatusCodes.Status400BadRequest)
              .ProducesProblem(StatusCodes.Status401Unauthorized)
              .ProducesProblem(StatusCodes.Status404NotFound);

        return routes;
    }

    private static async Task<Results<Ok<UpdateMeasurementsResult>, ValidationProblem, NotFound<ProblemDetails>>> HandleAsync(
        [FromBody]                         UpdateMeasurementsRequest       request,
        IValidator<UpdateMeasurementsCommand>                              validator,
        ISender                                                            sender,
        HttpContext                                                        httpContext,
        IProblemDetailsService                                             problemDetails,
        CancellationToken                                                  ct)
    {
        var userId = httpContext.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                     ?? string.Empty;

        var command = new UpdateMeasurementsCommand(
            userId,
            request.ChestCircumference,
            request.WaistCircumference,
            request.HipCircumference,
            request.ShoulderWidth);

        var validation = await validator.ValidateAsync(command, ct);
        if (!validation.IsValid)
            return TypedResults.ValidationProblem(validation.ToDictionary());

        try
        {
            var result = await sender.Send(command, ct);
            return TypedResults.Ok(result);
        }
        catch (KeyNotFoundException ex)
        {
            return TypedResults.NotFound(new ProblemDetails
            {
                Title  = "Profile not found",
                Detail = ex.Message,
                Status = StatusCodes.Status404NotFound,
                Type   = "https://tools.ietf.org/html/rfc7807"
            });
        }
    }
}
