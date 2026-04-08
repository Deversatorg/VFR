using ApplicationAuth.Features.Payments.Webhook;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Stripe;
using System.Threading;

namespace ApplicationAuth.Features.Payments.Webhook
{
    public static class StripeWebhookEndpoint
    {
        public static void MapStripeWebhookEndpoint(this IEndpointRouteBuilder app)
        {
            app.MapPost("/api/v1/payments/webhook", async (
                HttpContext httpContext,
                [FromServices] StripeWebhookHandler handler,
                [FromServices] Microsoft.Extensions.Logging.ILogger<StripeWebhookHandler> logger) =>
            {
                var signature = httpContext.Request.Headers["Stripe-Signature"].ToString();
                try
                {
                    await handler.HandleAsync(httpContext.Request.Body, signature, httpContext.RequestAborted);
                    return Results.Ok();
                }
                catch (Stripe.StripeException ex)
                {
                    // Bad signature → 400 tells Stripe to stop retrying
                    logger.LogWarning(ex, "Stripe webhook signature validation failed");
                    return Results.BadRequest("Webhook signature validation failed");
                }
                catch (InvalidOperationException ex)
                {
                    // Misconfiguration (e.g. missing Stripe keys) → 503 signals temporary issue
                    logger.LogError(ex, "Stripe webhook processing failed due to misconfiguration");
                    return Results.StatusCode(StatusCodes.Status503ServiceUnavailable);
                }
            })
            .AllowAnonymous()    // Stripe calls this without Bearer token
            .WithSummary("Stripe Webhook")
            .WithDescription("Receives Stripe webhook events. Validates Stripe-Signature header.");
        }
    }
}
