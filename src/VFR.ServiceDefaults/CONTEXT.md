# VFR.ServiceDefaults Context

Updated: 2026-03-20

## Role

Shared Aspire defaults for the net9 service slice. This project adds service discovery, resilience, health checks, and OpenTelemetry defaults.

## Important file

- `Extensions.cs`

## Used by

- `src/VFR.ProfileApi`
- potentially any future net9 services in this workspace

## Current issues

- There is a parallel net8 copy in `src/VFR.Auth/ApplicationAuth.ServiceDefaults`.
- gRPC client instrumentation is commented out.
- This duplication increases maintenance cost while the repo stays split across net8 and net9.

## Open next

- `Extensions.cs`
- `../VFR.Auth/ApplicationAuth.ServiceDefaults/CONTEXT.md`
