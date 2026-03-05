using MediatR;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using System.Security.Claims;

namespace VFR.ProfileApi.Features.GetProfile;

public static class GetProfileEndpoint
{
    public static void MapGetProfile(this IEndpointRouteBuilder app)
    {
        app.MapGet("/me", async (ISender sender, ClaimsPrincipal user) =>
        {
            // Extract Subject (User ID) from JWT token
            var subClaim = user.FindFirst(ClaimTypes.NameIdentifier) ?? user.FindFirst("sub");
            if (subClaim is null || string.IsNullOrWhiteSpace(subClaim.Value))
            {
                return Results.Unauthorized();
            }

            var userId = subClaim.Value;
            var result = await sender.Send(new GetProfileQuery(userId));

            if (result is null)
            {
                return Results.NotFound(new { Detail = "Profile not found for current user." });
            }

            return Results.Ok(result);
        })
        .RequireAuthorization()
        .WithName("GetProfile")
        .Produces<GetProfileResponse>(StatusCodes.Status200OK)
        .Produces(StatusCodes.Status401Unauthorized)
        .Produces(StatusCodes.Status404NotFound);
    }
}
