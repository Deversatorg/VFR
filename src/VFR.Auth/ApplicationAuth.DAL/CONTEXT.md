# ApplicationAuth.DAL Context

Updated: 2026-03-21

## Role

Data-access layer for the auth slice. This is where the EF Core context, migrations, and persistence-side interceptors live.

## Important files

- `DataContext.cs`
- `Abstract/IDataContext.cs`
- `Interceptors/AuditableEntityInterceptor.cs`
- `Migrations/*`

## Current issues

- Startup migrations are triggered from `ApplicationAuth/Program.cs`, so migration changes are high-impact.
- The project has been trimmed toward SDK-style package references, but startup bootstrap logic still makes persistence changes here high-risk.
- Any entity change here usually requires coordinated updates in the domain layer and API handlers.

## Open next

- `DataContext.cs`
- `Migrations/DataContextModelSnapshot.cs`
- `../ApplicationAuth.Domain/CONTEXT.md`
