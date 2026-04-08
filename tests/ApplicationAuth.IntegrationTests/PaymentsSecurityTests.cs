using System.Net;
using System.Security.Cryptography;
using System.Text;
using ApplicationAuth.DAL;
using ApplicationAuth.Domain.Entities.Identity;
using ApplicationAuth.Features.Payments.Webhook;
using ApplicationAuth.SharedModels.Enums;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Stripe;
using Xunit;
using PlanEntity = ApplicationAuth.Domain.Entities.Identity.Plan;
using SubscriptionEntity = ApplicationAuth.Domain.Entities.Identity.Subscription;

namespace ApplicationAuth.IntegrationTests;

public sealed class PaymentsSecurityTests
{
    private const string WebhookSecret = "whsec_test_123";

    [Fact]
    public async Task StripeWebhookHandler_ThrowsInvalidOperationException_WhenStripeSecretMissing()
    {
        var dbName = $"payments-security-missing-secret-{Guid.NewGuid():N}";
        await using var db = CreateDbContext(dbName);
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Stripe:WebhookSecret"] = WebhookSecret,
            })
            .Build();
        var handler = new StripeWebhookHandler(db, config, NullLogger<StripeWebhookHandler>.Instance);

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            handler.HandleAsync(new MemoryStream(Encoding.UTF8.GetBytes("{}")), string.Empty, CancellationToken.None));
    }

    [Fact]
    public async Task StripeWebhookHandler_ThrowsStripeException_WhenSignatureIsInvalid()
    {
        var dbName = $"payments-security-bad-signature-{Guid.NewGuid():N}";
        await using var db = CreateDbContext(dbName);
        var handler = CreateWebhookHandler(db);
        var payload = BuildSubscriptionUpdatedPayload(
            eventId: "evt_bad_signature",
            eventCreatedUnixSeconds: DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            stripeSubscriptionId: "sub_bad_signature",
            customerId: "cus_bad_signature",
            status: "active");

        await Assert.ThrowsAsync<StripeException>(() =>
            handler.HandleAsync(CreatePayloadStream(payload), "t=1,v1=invalid", CancellationToken.None));
    }

    [Fact]
    public async Task StripeWebhookHandler_MatchesIncompleteSubscriptionBySubscriptionRecordIdMetadata()
    {
        var dbName = $"payments-security-match-{Guid.NewGuid():N}";
        await using var db = CreateDbContext(dbName);

        var user = CreateUser(1001, "match@example.com");
        var basicPlan = CreatePlan(2001, "Basic");
        var proPlan = CreatePlan(2002, "Pro");
        db.Set<ApplicationUser>().Add(user);
        db.Set<PlanEntity>().AddRange(basicPlan, proPlan);

        var targetSubscription = new SubscriptionEntity
        {
            UserId = user.Id,
            PlanId = basicPlan.Id,
            StripeCustomerId = "cus_match",
            StripeSubscriptionId = string.Empty,
            Status = SubscriptionStatus.Incomplete,
            CreatedAt = DateTime.UtcNow.AddMinutes(-10),
            UpdatedAt = DateTime.UtcNow.AddMinutes(-10)
        };
        var competingSubscription = new SubscriptionEntity
        {
            UserId = user.Id,
            PlanId = proPlan.Id,
            StripeCustomerId = "cus_match",
            StripeSubscriptionId = string.Empty,
            Status = SubscriptionStatus.Incomplete,
            CreatedAt = DateTime.UtcNow.AddMinutes(-5),
            UpdatedAt = DateTime.UtcNow.AddMinutes(-5)
        };
        db.Set<SubscriptionEntity>().AddRange(targetSubscription, competingSubscription);
        await db.SaveChangesAsync();

        var handler = CreateWebhookHandler(db);
        var stripeEvent = new Event
        {
            Id = "evt_match_by_subscription_record",
            Type = "customer.subscription.updated",
            Created = DateTimeOffset.FromUnixTimeSeconds(200).UtcDateTime,
            Data = new EventData
            {
                Object = new Stripe.Subscription
                {
                    Id = "sub_live_target",
                    CustomerId = "cus_match",
                    Status = "active",
                    CancelAtPeriodEnd = false,
                    CurrentPeriodStart = DateTimeOffset.FromUnixTimeSeconds(200).UtcDateTime,
                    CurrentPeriodEnd = DateTimeOffset.FromUnixTimeSeconds(3800).UtcDateTime,
                    Metadata = new Dictionary<string, string>
                    {
                        ["subscriptionRecordId"] = targetSubscription.Id.ToString(),
                        ["userId"] = user.Id.ToString(),
                        ["planId"] = basicPlan.Id.ToString(),
                    }
                }
            }
        };

        await handler.HandleParsedEventAsync(stripeEvent, CancellationToken.None);

        var updatedTarget = await db.Set<SubscriptionEntity>().SingleAsync(x => x.Id == targetSubscription.Id);
        var untouchedCompeting = await db.Set<SubscriptionEntity>().SingleAsync(x => x.Id == competingSubscription.Id);

        Assert.Equal(SubscriptionStatus.Active, updatedTarget.Status);
        Assert.Equal("sub_live_target", updatedTarget.StripeSubscriptionId);
        Assert.Equal("evt_match_by_subscription_record", updatedTarget.LastStripeEventId);
        Assert.Equal(DateTimeOffset.FromUnixTimeSeconds(200).UtcDateTime, updatedTarget.LastStripeEventCreatedAt);
        Assert.Equal(SubscriptionStatus.Incomplete, untouchedCompeting.Status);
        Assert.True(string.IsNullOrWhiteSpace(untouchedCompeting.StripeSubscriptionId));
    }

    [Fact]
    public async Task StripeWebhookHandler_UsesLastStripeEventTimestampInsteadOfUpdatedAtForOrdering()
    {
        var dbName = $"payments-security-ordering-{Guid.NewGuid():N}";
        await using var db = CreateDbContext(dbName);

        var user = CreateUser(1101, "ordering@example.com");
        var plan = CreatePlan(2101, "Ordering");
        db.Set<ApplicationUser>().Add(user);
        db.Set<PlanEntity>().Add(plan);

        var subscription = new SubscriptionEntity
        {
            UserId = user.Id,
            PlanId = plan.Id,
            StripeCustomerId = "cus_ordering",
            StripeSubscriptionId = "sub_ordering",
            Status = SubscriptionStatus.PastDue,
            LastStripeEventId = "evt_old",
            LastStripeEventCreatedAt = DateTimeOffset.FromUnixTimeSeconds(100).UtcDateTime,
            CreatedAt = DateTime.UtcNow.AddMinutes(-10),
            UpdatedAt = DateTime.UtcNow
        };
        db.Set<SubscriptionEntity>().Add(subscription);
        await db.SaveChangesAsync();

        var handler = CreateWebhookHandler(db);
        var stripeEvent = new Event
        {
            Id = "evt_newer_than_last_stripe_event",
            Type = "invoice.payment_succeeded",
            Created = DateTimeOffset.FromUnixTimeSeconds(200).UtcDateTime,
            Data = new EventData
            {
                Object = new Invoice
                {
                    SubscriptionId = subscription.StripeSubscriptionId
                }
            }
        };

        await handler.HandleParsedEventAsync(stripeEvent, CancellationToken.None);

        var updatedSubscription = await db.Set<SubscriptionEntity>().SingleAsync(x => x.Id == subscription.Id);
        Assert.Equal(SubscriptionStatus.Active, updatedSubscription.Status);
        Assert.Equal("evt_newer_than_last_stripe_event", updatedSubscription.LastStripeEventId);
        Assert.Equal(DateTimeOffset.FromUnixTimeSeconds(200).UtcDateTime, updatedSubscription.LastStripeEventCreatedAt);
    }

    private static DataContext CreateDbContext(string databaseName)
    {
        var options = new DbContextOptionsBuilder<DataContext>()
            .UseInMemoryDatabase(databaseName)
            .Options;

        var db = new DataContext(options);
        db.Database.EnsureCreated();
        return db;
    }

    private static ApplicationUser CreateUser(int id, string email) =>
        new()
        {
            Id = id,
            UserName = email,
            Email = email,
            NormalizedEmail = email.ToUpperInvariant(),
            NormalizedUserName = email.ToUpperInvariant(),
            EmailConfirmed = true,
            IsActive = true,
            RegistratedAt = DateTime.UtcNow
        };

    private static PlanEntity CreatePlan(int id, string name) =>
        new()
        {
            Id = id,
            Name = name,
            IsActive = true,
            AmountCents = 999,
            Currency = "usd",
            Interval = PlanInterval.Monthly,
            CreatedAt = DateTime.UtcNow
        };

    private static StripeWebhookHandler CreateWebhookHandler(DataContext db)
    {
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Stripe:SecretKey"] = "sk_test_123",
                ["Stripe:WebhookSecret"] = WebhookSecret,
            })
            .Build();

        return new StripeWebhookHandler(db, config, NullLogger<StripeWebhookHandler>.Instance);
    }

    private static string BuildSubscriptionUpdatedPayload(
        string eventId,
        long eventCreatedUnixSeconds,
        string stripeSubscriptionId,
        string customerId,
        string status) =>
        $$"""
        {
          "id": "{{eventId}}",
          "object": "event",
          "type": "customer.subscription.updated",
          "created": {{eventCreatedUnixSeconds}},
          "data": {
            "object": {
              "id": "{{stripeSubscriptionId}}",
              "object": "subscription",
              "customer": "{{customerId}}",
              "status": "{{status}}",
              "cancel_at_period_end": false,
              "current_period_start": {{eventCreatedUnixSeconds}},
              "current_period_end": {{eventCreatedUnixSeconds + 3600}},
              "metadata": {}
            }
          }
        }
        """;

    private static MemoryStream CreatePayloadStream(string payload) =>
        new(Encoding.UTF8.GetBytes(payload));
}
