# VFR.ProfileApi Context

Updated: 2026-04-25

## Role

Minimal API service for user body/profile data, quick setup, manual and auto measurements, Studio draft persistence, and Studio avatar generation brokering.

## Entry points

- `Program.cs`
- `Features/GetProfile`
- `Features/QuickSetup`
- `Features/UpdateMeasurements`
- `Features/UpsertStudioProfile`
- `Features/StudioAvatarGeneration`
- `Infrastructure`

## Stack

- .NET 9
- Minimal APIs
- MediatR
- FluentValidation
- EF Core + PostgreSQL
- Redis client via Aspire

## Ownership boundary

- This service owns profile data, Studio draft state, avatar generation brokering, and the persisted metadata about the last generated avatar for a draft.
- It calls the AI engine over HTTP for avatar enqueue/status and derives the generation user id from the authenticated ProfileApi user.
- Studio upsert intentionally ignores client-supplied generated-avatar metadata. Only the broker endpoint may persist generated-avatar fields after AI `SUCCESS`, a fetchable `model_url`, and a matching current draft hash.
- Avatar generation task ownership is Redis-backed outside `Testing` with a 2 hour TTL. The `Testing` environment keeps the in-memory tracker so integration tests do not need Redis.

## Test status

- There is a dedicated integration test project in `tests/VFR.ProfileApi.IntegrationTests`.
- Those tests passed on 2026-03-21.
- `Program.cs` now falls back to a deterministic test signing key in `Testing` environment so the host can build under `WebApplicationFactory`.
- `DatabaseBootstrapControl` lets tests skip PostgreSQL migrations during host startup.

## Current issues

- Startup migrations still happen in `Program.cs` unless tests disable them through `DatabaseBootstrapControl`.
- JWT config must stay aligned with the auth service and AppHost.
- The project is on .NET 9 while auth is still on .NET 8.
- The related net9 tests emit an EF Core Relational 9.0.2 vs 9.0.3 warning.
- Studio-generated avatar state is persisted here after the AI engine returns a fetchable model URL.

## Open next

- `Program.cs`
- `DatabaseBootstrapControl.cs`
- `Features/Studio/StudioDraftStateHasher.cs`
- `Features/UpsertStudioProfile`
- `Features/StudioAvatarGeneration`
- `Infrastructure/ProfileDbContext.cs`
