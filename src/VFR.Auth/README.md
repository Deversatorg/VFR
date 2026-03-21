# ApplicationAuth

Authentication and account service for the Virtual Fitting Room workspace.

## Current Scope

- User and admin authentication
- JWT session issuance and refresh
- Email verification and password recovery
- Social login
- Admin user management
- Billing and subscription endpoints
- Telegram integration

## Runtime Notes

- Framework: .NET 8
- Database: PostgreSQL via EF Core
- API style: Minimal APIs + MediatR handlers
- Hosting: launched through the workspace AppHost

## Important

- This service is not a generic template anymore; it contains project-specific flows and legacy areas.
- Prefer running it through the main workspace host instead of relying on older standalone-template assumptions.
