---
name: auth-security
description: Find auth exploits, JWT flaws, webhook risks, and billing security issues in VFR.Auth. Use for security-focused review of auth, payments, and bootstrap behavior.
---

# Auth Security

Do NOT use this skill when:

- the goal is general .NET code quality or test coverage → use `dotnet-review`
- the change is in `src/VFR.AiEngine` → use `ai-engine-security`

Read these first:

- `src/VFR.Auth/CONTEXT.md`
- `src/VFR.Auth/ApplicationAuth/CONTEXT.md`
- `agents/references/auth-trust-boundaries.md`

## Entry Points

- `src/VFR.Auth/ApplicationAuth/Program.cs`
- `src/VFR.Auth/ApplicationAuth/Features/Test/TestEndpoint.cs`
- touched files under `Features/Account`
- touched files under `Features/AdminUsers`
- touched files under `Features/Payments`
- touched files under `Features/Telegram`
- `src/VFR.Auth/ApplicationAuth/Features/Payments/Checkout/CreateCheckoutSessionHandler.cs`
- `src/VFR.Auth/ApplicationAuth/Features/Payments/Webhook/StripeWebhookEndpoint.cs`
- `src/VFR.Auth/ApplicationAuth/Features/Payments/Webhook/StripeWebhookHandler.cs`
- `src/VFR.Auth/ApplicationAuth/Features/Payments/Shared/StripeService.cs`
- `src/VFR.Auth/ApplicationAuth/Features/Payments/Shared/MockStripeService.cs`

## Risks

### Auth and JWT

- `Testing` or development-only behavior leaking into normal runtime
- dangerous test endpoints becoming reachable without tight gating
- JWT issuer, audience, lifetime, or signing-key drift
- CORS policies becoming broader than intended
- bootstrap admin or seed behavior running in the wrong environment
- admin or billing endpoints missing authorization or assuming the wrong role shape
- external-provider errors or secrets leaking through logs or responses

### Payments and Webhooks

- mock mode bypassing signature validation outside controlled development use
- webhook secret or Stripe secret assumptions silently changing behavior
- subscription records being matched too loosely or updated into the wrong state
- checkout success/cancel URLs falling back to localhost in unintended environments
- missing idempotency or replay-safe behavior around repeated webhook delivery
- logs exposing sensitive Stripe payload details or identifiers unnecessarily
- endpoint auth assumptions drifting even though webhook is intentionally anonymous

Prefer concrete exploit paths and configuration mistakes over generic best practices.
Treat payment-state transitions as correctness and security sensitive.
