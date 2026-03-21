# VFR.ProfileApi.IntegrationTests Context

Updated: 2026-03-21

## Role

Minimal integration tests for the profile API using `WebApplicationFactory`, in-memory EF Core, and a fake auth handler.

## What these tests cover

- missing profile returns 404
- quick setup creates a profile that can be fetched
- studio profile upsert stores manual and auto measurements
- draft-only save preserves the previous generated avatar but marks it stale

## Important files

- `ProfileApiWebApplicationFactory.cs`
- `ProfileEndpointsTests.cs`
- `TestAuthHandler.cs`

## Current state

- This project passed on 2026-03-21.
- The harness now depends on `Testing` environment startup behavior in `VFR.ProfileApi/Program.cs` so the host can build before services are replaced for tests.

## Extra note

- This project still emits an EF Core Relational 9.0.2 vs 9.0.3 warning.

## Open next

- `ProfileApiWebApplicationFactory.cs`
- `ProfileEndpointsTests.cs`
- `../../src/VFR.ProfileApi/CONTEXT.md`
