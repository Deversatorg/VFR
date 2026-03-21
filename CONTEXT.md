# Repo Context

Updated: 2026-03-21

## What this repo is

This is the active virtual fitting room workspace with:

- `src/vfr-web`: React 19 + Vite Studio and wardrobe app
- `src/VFR.Auth`: .NET 8 auth, payments, and Telegram slice
- `src/VFR.ProfileApi`: .NET 9 profile and Studio draft API
- `src/VFR.AiEngine`: Python FastAPI + Celery avatar pipeline
- `src/VFR.AppHost`: Aspire composition root for the local stack

## Best entry point

- Start from `src/VFR.AppHost/VFR.AppHost.csproj` for the real local runtime graph.
- `global.json` pins the .NET SDK to `9.0.311`, so use that before building the host.
- After opening AppHost, jump into the target slice `CONTEXT.md`.

## Active runtime paths

- AppHost wires PostgreSQL, Redis, auth, profile API, AI engine, AI worker, and `src/vfr-web`.
- `src/vfr-web` is the live frontend. `src/VFR.Web` is not part of the active path.
- The browser currently talks directly to:
- `ApplicationAuth` over HTTP for auth and billing.
- `VFR.ProfileApi` over HTTP for profile and Studio draft persistence.
- `VFR.AiEngine` over HTTP for avatar enqueue and status polling.
- `VFR.ProfileApi` stores the Studio draft and generated avatar metadata, but it still does not broker AI generation.

## Current test picture

- `tests/ApplicationAuth.IntegrationTests` passed on 2026-03-21.
- `tests/VFR.ProfileApi.IntegrationTests` passed on 2026-03-21.
- `tests/VFR.ApiFlowTests` passed on 2026-03-21.
- `src/VFR.AiEngine/tests/test_status_endpoints.py` covers queue/HTTP contracts.
- `src/VFR.AiEngine/tests/test_proxy_targets.py` passed inside the AI container on 2026-03-21.
- The net9 test projects still emit an EF Core Relational 9.0.2 vs 9.0.3 warning.
- These .NET test projects should be run sequentially because parallel runs can lock shared outputs.

## Main current problems

- The workspace still mixes .NET 8 auth projects with .NET 9 AppHost/profile projects.
- The frontend is aware of the internal AI boundary because avatar generation bypasses the profile API.
- Auth and profile services still contain startup bootstrap logic that tests have to disable explicitly.
- AI body composition is now driven by proxy anthropometric targets, but the shoulder/bicep/thigh loops are still partly placeholder-based.
- Config remains split between AppHost configuration, service appsettings, and Python env variables.

## First files to open

- `src/VFR.AppHost/Program.cs`
- `src/vfr-web/src/pages/studio/Studio.tsx`
- `src/VFR.ProfileApi/Program.cs`
- `src/VFR.ProfileApi/Features/UpsertStudioProfile`
- `src/VFR.AiEngine/ml_pipeline.py`
- `src/VFR.Auth/ApplicationAuth/Program.cs`
- `docs/runtime-config.md`
