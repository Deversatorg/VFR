# ApplicationAuth.ServiceDefaults Context

Updated: 2026-03-20

## Role

Net8 copy of the service-default helpers used by the auth slice.

## Important file

- `Extensions.cs`

## Current issues

- This duplicates the same idea already present in `src/VFR.ServiceDefaults`.
- The duplication exists because auth is still on .NET 8 while the other services are on .NET 9.
- Any change to resilience, telemetry, or discovery defaults may need to be applied in two places.

## Open next

- `Extensions.cs`
- `../../VFR.ServiceDefaults/CONTEXT.md`
