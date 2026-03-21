# VFR.ProfileApi Context

Updated: 2026-03-21

## Role

Minimal API service for user body/profile data, quick setup, manual and auto measurements, and Studio draft persistence.

## Entry points

- `Program.cs`
- `Features/GetProfile`
- `Features/QuickSetup`
- `Features/UpdateMeasurements`
- `Features/UpsertStudioProfile`
- `Infrastructure`

## Stack

- .NET 9
- Minimal APIs
- MediatR
- FluentValidation
- EF Core + PostgreSQL
- Redis client via Aspire

## Ownership boundary

- This service owns profile data, Studio draft state, and the persisted metadata about the last generated avatar for a draft.
- It does not currently own AI enqueue. The frontend calls the AI engine directly.

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
- Studio-generated avatar state is intentionally persistence-only here. The actual generation workflow still lives in the browser + AI engine boundary.

## Open next

- `Program.cs`
- `DatabaseBootstrapControl.cs`
- `Features/Studio/StudioDraftStateHasher.cs`
- `Features/UpsertStudioProfile`
- `Infrastructure/ProfileDbContext.cs`
