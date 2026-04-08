using ApplicationAuth.Common.Constants;
using ApplicationAuth.DAL.Abstract;
using ApplicationAuth.Domain.Entities.Identity;
using ApplicationAuth.SharedModels.Enums;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Stripe;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace ApplicationAuth.Features.Payments.Webhook
{
    /// <summary>
    /// Handles incoming Stripe webhook events and updates subscription state in DB.
    /// </summary>
    public class StripeWebhookHandler
    {
        private readonly IDataContext _db;
        private readonly IConfiguration _config;
        private readonly ILogger<StripeWebhookHandler> _logger;

        public StripeWebhookHandler(IDataContext db, IConfiguration config, ILogger<StripeWebhookHandler> logger)
        {
            _db = db;
            _config = config;
            _logger = logger;
        }

        public async Task HandleAsync(Stream requestBody, string stripeSignature, CancellationToken ct)
        {
            var webhookSecret = _config["Stripe:WebhookSecret"];
            var isMockMode = string.IsNullOrEmpty(_config["Stripe:SecretKey"]);

            Event stripeEvent;

            if (isMockMode)
            {
                _logger.LogError(
                    "Stripe webhook received but Stripe:SecretKey is not configured. " +
                    "Webhooks cannot be validated or processed in mock mode. " +
                    "If this is production, set Stripe:SecretKey and Stripe:WebhookSecret.");
                throw new InvalidOperationException(
                    "Stripe is not configured. Cannot validate or process webhooks.");
            }

            try
            {
                var json = await new StreamReader(requestBody).ReadToEndAsync(ct);
                stripeEvent = EventUtility.ConstructEvent(json, stripeSignature, webhookSecret);
            }
            catch (StripeException ex)
            {
                _logger.LogWarning(ex, "Stripe webhook signature validation failed");
                throw;
            }

            await HandleParsedEventAsync(stripeEvent, ct);
        }

        internal async Task HandleParsedEventAsync(Event stripeEvent, CancellationToken ct)
        {
            _logger.LogInformation("Stripe webhook received: {EventType}", stripeEvent.Type);

            switch (stripeEvent.Type)
            {
                case StripeWebhookType.SubscriptionCreated:
                case StripeWebhookType.SubscriptionUpdated:
                    await HandleSubscriptionUpdatedAsync(stripeEvent, ct);
                    break;

                case StripeWebhookType.SubscriptionDeleted:
                    await HandleSubscriptionDeletedAsync(stripeEvent, ct);
                    break;

                case StripeWebhookType.InvoicePaymentSucceeded:
                    await HandleInvoicePaymentSucceededAsync(stripeEvent, ct);
                    break;

                case StripeWebhookType.InvoicePaymentFailed:
                    await HandleInvoicePaymentFailedAsync(stripeEvent, ct);
                    break;

                default:
                    _logger.LogDebug("Unhandled Stripe event type: {EventType}", stripeEvent.Type);
                    break;
            }
        }

        private async Task HandleSubscriptionUpdatedAsync(Event evt, CancellationToken ct)
        {
            var stripeSub = evt.Data.Object as Stripe.Subscription;
            if (stripeSub == null)
            {
                return;
            }

            var sub = await FindOrCreateSubscriptionAsync(stripeSub, ct);
            if (sub == null || ShouldIgnoreStripeEvent(sub, evt))
            {
                return;
            }

            sub.StripeSubscriptionId = stripeSub.Id;
            sub.Status = MapStatus(stripeSub.Status);
            sub.CurrentPeriodStart = stripeSub.CurrentPeriodStart;
            sub.CurrentPeriodEnd = stripeSub.CurrentPeriodEnd;
            sub.CancelAtPeriodEnd = stripeSub.CancelAtPeriodEnd;
            MarkStripeEventProcessed(sub, evt);

            await _db.SaveChangesAsync(ct);
            _logger.LogInformation("Subscription {SubId} updated -> {Status}", stripeSub.Id, sub.Status);
        }

        private async Task HandleSubscriptionDeletedAsync(Event evt, CancellationToken ct)
        {
            var stripeSub = evt.Data.Object as Stripe.Subscription;
            if (stripeSub == null)
            {
                return;
            }

            var sub = await _db.Set<Domain.Entities.Identity.Subscription>()
                .FirstOrDefaultAsync(s => s.StripeSubscriptionId == stripeSub.Id, ct);

            if (sub == null || ShouldIgnoreStripeEvent(sub, evt))
            {
                return;
            }

            sub.Status = SubscriptionStatus.Canceled;
            MarkStripeEventProcessed(sub, evt);

            await _db.SaveChangesAsync(ct);
            _logger.LogInformation("Subscription {SubId} canceled", stripeSub.Id);
        }

        private async Task HandleInvoicePaymentSucceededAsync(Event evt, CancellationToken ct)
        {
            var invoice = evt.Data.Object as Invoice;
            if (invoice?.SubscriptionId == null)
            {
                return;
            }

            var sub = await _db.Set<Domain.Entities.Identity.Subscription>()
                .FirstOrDefaultAsync(s => s.StripeSubscriptionId == invoice.SubscriptionId, ct);

            if (sub == null || ShouldIgnoreStripeEvent(sub, evt))
            {
                return;
            }

            sub.Status = SubscriptionStatus.Active;
            MarkStripeEventProcessed(sub, evt);

            await _db.SaveChangesAsync(ct);
            _logger.LogInformation("Payment succeeded for subscription {SubId}", invoice.SubscriptionId);
        }

        private async Task HandleInvoicePaymentFailedAsync(Event evt, CancellationToken ct)
        {
            var invoice = evt.Data.Object as Invoice;
            if (invoice?.SubscriptionId == null)
            {
                return;
            }

            var sub = await _db.Set<Domain.Entities.Identity.Subscription>()
                .FirstOrDefaultAsync(s => s.StripeSubscriptionId == invoice.SubscriptionId, ct);

            if (sub == null || ShouldIgnoreStripeEvent(sub, evt))
            {
                return;
            }

            sub.Status = SubscriptionStatus.PastDue;
            MarkStripeEventProcessed(sub, evt);

            await _db.SaveChangesAsync(ct);
            _logger.LogWarning("Payment failed for subscription {SubId}", invoice.SubscriptionId);
        }

        private async Task<Domain.Entities.Identity.Subscription?> FindOrCreateSubscriptionAsync(Stripe.Subscription stripeSub, CancellationToken ct)
        {
            var sub = await _db.Set<Domain.Entities.Identity.Subscription>()
                .FirstOrDefaultAsync(s => s.StripeSubscriptionId == stripeSub.Id, ct);

            if (sub != null)
            {
                return sub;
            }

            if (TryGetMetadataInt(stripeSub.Metadata, "subscriptionRecordId", out var subscriptionRecordId))
            {
                sub = await _db.Set<Domain.Entities.Identity.Subscription>()
                    .FirstOrDefaultAsync(s => s.Id == subscriptionRecordId && s.Status == SubscriptionStatus.Incomplete, ct);

                if (sub != null)
                {
                    return sub;
                }

                _logger.LogWarning(
                    "Stripe subscription {StripeSubscriptionId} referenced local subscription {SubscriptionRecordId}, but no incomplete record was found.",
                    stripeSub.Id,
                    subscriptionRecordId);
            }

            if (TryGetMetadataInt(stripeSub.Metadata, "userId", out var userId))
            {
                IQueryable<Domain.Entities.Identity.Subscription> query = _db.Set<Domain.Entities.Identity.Subscription>()
                    .Where(s => s.UserId == userId && s.Status == SubscriptionStatus.Incomplete);

                if (TryGetMetadataInt(stripeSub.Metadata, "planId", out var planId))
                {
                    query = query.Where(s => s.PlanId == planId);
                }

                var userScopedMatches = await query
                    .OrderByDescending(s => s.CreatedAt)
                    .Take(2)
                    .ToListAsync(ct);

                if (userScopedMatches.Count == 1)
                {
                    return userScopedMatches[0];
                }

                if (userScopedMatches.Count > 1)
                {
                    _logger.LogWarning(
                        "Ambiguous incomplete subscription match for Stripe subscription {StripeSubscriptionId}. Metadata userId={UserId}, planId={PlanId}.",
                        stripeSub.Id,
                        userId,
                        TryGetMetadataInt(stripeSub.Metadata, "planId", out var metadataPlanId) ? metadataPlanId : null);
                    return null;
                }
            }

            var customerMatches = await _db.Set<Domain.Entities.Identity.Subscription>()
                .Where(s => s.StripeCustomerId == stripeSub.CustomerId && s.Status == SubscriptionStatus.Incomplete)
                .OrderByDescending(s => s.CreatedAt)
                .Take(2)
                .ToListAsync(ct);

            if (customerMatches.Count == 1)
            {
                return customerMatches[0];
            }

            if (customerMatches.Count > 1)
            {
                _logger.LogWarning(
                    "Ambiguous incomplete subscription match by Stripe customer ID for Stripe subscription {StripeSubscriptionId} and customer {StripeCustomerId}.",
                    stripeSub.Id,
                    stripeSub.CustomerId);
            }

            return null;
        }

        private bool ShouldIgnoreStripeEvent(Domain.Entities.Identity.Subscription subscription, Event evt)
        {
            if (!string.IsNullOrWhiteSpace(subscription.LastStripeEventId) &&
                string.Equals(subscription.LastStripeEventId, evt.Id, StringComparison.Ordinal))
            {
                _logger.LogInformation(
                    "Ignoring duplicate Stripe event {EventId} for subscription record {SubscriptionId}.",
                    evt.Id,
                    subscription.Id);
                return true;
            }

            var eventCreatedAt = GetStripeEventCreatedAt(evt);
            if (subscription.LastStripeEventCreatedAt.HasValue &&
                eventCreatedAt < subscription.LastStripeEventCreatedAt.Value)
            {
                _logger.LogInformation(
                    "Ignoring outdated Stripe event {EventId} for subscription record {SubscriptionId}. Event created at {EventCreatedAt:o}, last processed at {LastProcessedAt:o}.",
                    evt.Id,
                    subscription.Id,
                    eventCreatedAt,
                    subscription.LastStripeEventCreatedAt.Value);
                return true;
            }

            return false;
        }

        private static void MarkStripeEventProcessed(Domain.Entities.Identity.Subscription subscription, Event evt)
        {
            subscription.LastStripeEventId = evt.Id;
            subscription.LastStripeEventCreatedAt = GetStripeEventCreatedAt(evt);
            subscription.UpdatedAt = DateTime.UtcNow;
        }

        private static DateTime GetStripeEventCreatedAt(Event evt) =>
            evt.Created.Kind == DateTimeKind.Utc
                ? evt.Created
                : evt.Created.ToUniversalTime();

        private static bool TryGetMetadataInt(IDictionary<string, string> metadata, string key, out int value)
        {
            value = default;
            return metadata is not null
                && metadata.TryGetValue(key, out var rawValue)
                && int.TryParse(rawValue, out value);
        }

        private static SubscriptionStatus MapStatus(string stripeStatus) => stripeStatus switch
        {
            "active" => SubscriptionStatus.Active,
            "trialing" => SubscriptionStatus.Trialing,
            "past_due" => SubscriptionStatus.PastDue,
            "canceled" => SubscriptionStatus.Canceled,
            "unpaid" => SubscriptionStatus.Unpaid,
            _ => SubscriptionStatus.Incomplete
        };
    }
}
