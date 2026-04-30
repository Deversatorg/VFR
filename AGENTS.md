# Virtual Fitting Room Agent Guide

Use this file as the shared operating guide for AI agents and human contributors working in this repository.

## Repo Map

- `src/vfr-web`: React 19 + Vite frontend for auth-adjacent flows, Studio draft editing, and avatar generation UX.
- `src/VFR.ProfileApi`: .NET 9 Minimal API for profile data, Studio draft persistence, avatar generation brokering, and generated-avatar metadata.
- `src/VFR.Auth`: .NET 8 auth, billing, admin, and Telegram slice.
- `src/VFR.AiEngine`: FastAPI + Celery + PyTorch/SMPL-X pipeline for avatar and garment generation.
- `src/VFR.AppHost`: Aspire composition root for the local runtime graph.

## Default Workflow

1. Read the nearest `CONTEXT.md` before changing a slice.
2. Identify the owning service before editing request/response shapes.
3. Change the smallest possible surface area first.
4. Verify the narrowest relevant checks, then widen if boundaries moved.
5. Review cross-service contracts whenever frontend, API DTOs, auth, or generation payloads change.
6. Record confirmed repo-specific lessons in `agents/learnings.md` instead of burying them in prompts.

## Current Ownership Boundaries

- `vfr-web` owns browser UX and local Studio state. It calls `VFR.ProfileApi` for Studio avatar generation.
- `VFR.ProfileApi` owns persisted profile data, Studio draft state, avatar generation brokering, and persisted metadata about the last generated avatar.
- `VFR.ProfileApi` calls `VFR.AiEngine` over HTTP for avatar enqueue/status and persists generated-avatar metadata only after a valid model URL is returned.
- `VFR.Auth` owns identity, tokens, billing, verification, admin flows, and related external integrations.
- `VFR.AiEngine` owns generation jobs, status polling, proxy-target measurement fitting, and artifact output paths.
- `VFR.AppHost` owns the local service graph, wiring, and shared runtime composition.

## Change Rules

- Do not move ownership across services implicitly. If ownership changes, update code, tests, and the relevant `CONTEXT.md`.
- Treat auth, profile, and AI request shapes as contracts. Verify both producer and consumer.
- Preserve `Testing`-environment startup behavior used by integration tests unless you update the tests at the same time.
- Keep AppHost, service appsettings, and Python env assumptions aligned when config changes.
- Prefer additive changes over broad refactors in `VFR.Auth`; it is the oldest and widest slice in the repo.
- Record confirmed repo-specific lessons in `agents/learnings.md` only when a test, incident, or repeated mistake proves the rule. Promote stable lessons into `AGENTS.md` or relevant skills over time.

## Verification Matrix

Run the smallest set that covers the changed boundary. Run .NET test projects sequentially in this repo.

- App graph or config wiring:
  `dotnet build src/VFR.AppHost/VFR.AppHost.csproj`
- Profile API changes:
  `dotnet test tests/VFR.ProfileApi.IntegrationTests/VFR.ProfileApi.IntegrationTests.csproj --no-restore`
- Auth changes:
  `dotnet test tests/ApplicationAuth.IntegrationTests/ApplicationAuth.IntegrationTests.csproj --no-restore`
- Cross-service HTTP flow changes:
  `dotnet test tests/VFR.ApiFlowTests/VFR.ApiFlowTests.csproj --no-restore`
- Frontend changes:
  `npm run build`
  `npm run lint`
  Run both from `src/vfr-web`
- AI engine Python syntax safety:
  `python -m compileall vfr_ai_engine`
  Run from `src/VFR.AiEngine`
- AI engine contract/helper tests:
  Prefer targeted tests under `src/VFR.AiEngine/tests`

## Review Priorities

- Contract drift between `vfr-web`, `VFR.ProfileApi`, and `VFR.AiEngine`
- JWT/token assumptions shared by `VFR.Auth`, `VFR.ProfileApi`, and tests
- Startup/bootstrap behavior that breaks `WebApplicationFactory` or local Aspire runs
- Local-path and missing-credential fallbacks that can hide deployment issues
- Expensive ML-path changes without narrow helper tests
- Silent frontend fallbacks that hide missing env wiring

## Suggested Agent Roles

- `frontend-worker`: `src/vfr-web`
- `dotnet-api-worker`: `src/VFR.ProfileApi`
- `auth-worker`: `src/VFR.Auth`
- `python-ai-worker`: `src/VFR.AiEngine`
- `reviewer`: read-only review and risk finding
- `contract-checker`: cross-service payload and ownership verification

Assign each role a clear write scope. Finish with one contract check if more than one slice changed.
