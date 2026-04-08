# Auth Trust Boundaries

Use this reference when reviewing `src/VFR.Auth`.

## Main Boundaries

- Browser to auth API over HTTP
- Auth API to PostgreSQL via EF Core
- Auth API to Stripe
- Stripe back to auth webhook endpoint
- Development/test callers to optional test endpoints

## Repo-Specific Security Hotspots

- `Program.cs` falls back to a deterministic JWT signing key in `Testing`; that must not leak into normal runtime.
- Test endpoints under `Features/Test` are anonymous and destructive. They are only safe behind strict development gating.
- Billing can run in mock mode when `Stripe:SecretKey` is absent. That is useful locally but dangerous if it changes production behavior silently.
- Checkout URLs can fall back to localhost values if config is missing.
- Startup does migrations, role seeding, bootstrap admin creation, and plan seeding unless explicitly disabled.
- CORS defaults to localhost-style origins when configured origins are absent.

## Review Questions

- Could an environment or config mistake expose test-only or mock-only behavior?
- Could JWT or role assumptions drift between auth, profile, and tests?
- Could a webhook, admin, or billing path update state without the intended proof of authority?
- Could logs or error responses leak provider details, secrets, or internal runtime state?
