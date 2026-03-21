# ApplicationAuth.IntegrationTests Context

Updated: 2026-03-21

## Role

Minimal integration tests for the auth API using `WebApplicationFactory` and an in-memory EF Core database.

## What these tests cover

- user registration
- verification token creation
- login after confirmation

## Important files

- `ApplicationAuthWebApplicationFactory.cs`
- `AuthEndpointsTests.cs`

## Current state

- This project passed on 2026-03-21.
- The harness relies on `Testing` environment startup behavior in `ApplicationAuth/Program.cs` plus the factory-level in-memory database swap.
- If it breaks again with a generic host-exit message, inspect auth startup prerequisites before touching the test methods.

## Open next

- `ApplicationAuthWebApplicationFactory.cs`
- `AuthEndpointsTests.cs`
- `../../src/VFR.Auth/ApplicationAuth/CONTEXT.md`
