# ApplicationAuth Context

Updated: 2026-03-21

## Role

Main auth web API for the workspace. It owns sessions, users, admin flows, billing endpoints, and some Telegram-related features.

## Entry points

- `Program.cs`
- `Features/Account`
- `Features/AdminUsers`
- `Features/Payments`
- `Features/Telegram`

## Stack

- .NET 8
- ASP.NET Core Minimal APIs
- MediatR
- FluentValidation
- ASP.NET Core Identity
- EF Core + PostgreSQL
- Serilog

## Important config

- `ConnectionStrings:Connection`
- `Jwt:Issuer`
- `Jwt:Audience`
- `Jwt:SigningKey`
- `BootstrapAdmin:Email`
- `BootstrapAdmin:Password`
- `Stripe:*`

## Test status

- `tests/ApplicationAuth.IntegrationTests` passed on 2026-03-21.
- `tests/VFR.ApiFlowTests` passed on 2026-03-21.
- `Program.cs` now falls back to a deterministic test signing key in `Testing` environment and can skip startup bootstrap work via `DatabaseBootstrapControl`.

## Current issues

- Startup still performs migrations, role seeding, bootstrap admin creation, and plan seeding unless disabled.
- The service surface is broad, so changes can break auth, billing, and admin flows at once.
- This project must stay aligned with AppHost and Profile API on JWT settings.
- There are dangerous test endpoints behind a config flag. Keep them off outside controlled dev usage.
- Telegram request/response contracts now live closer to the Telegram feature itself, so feature-local changes can ripple into handlers, serializer context, and endpoint contracts together.

## Open next

- `Program.cs`
- `DatabaseBootstrapControl.cs`
- `Features/Telegram`
- `../ApplicationAuth.DAL/CONTEXT.md`
- `../../../tests/ApplicationAuth.IntegrationTests/CONTEXT.md`
