# Runtime and Configuration Notes

This repository is split across multiple runtimes and service boundaries. The goal of this note is to make the current local setup explicit and to call out the places where config drift already exists.

## Runtime Matrix

| Component | Target/runtime | Notes |
| --- | --- | --- |
| `src/VFR.AppHost` | .NET 9 | Aspire host that wires PostgreSQL, Redis, the AI engine, the auth service, the profile API, and the Vite app. |
| `src/VFR.ServiceDefaults` | .NET 9 | Shared service defaults for Aspire apps. |
| `src/VFR.ProfileApi` | .NET 9 | Minimal API for profile, measurement, Studio draft, and avatar-generation broker flows. |
| `src/VFR.Protos` | .NET 9 | Shared gRPC contracts. |
| `src/VFR.Auth/ApplicationAuth*` | .NET 8 | Standalone auth and payments service subtree. |
| `src/vfr-web` | Node.js 20.19+ or 22.12+ | Vite 7 / React 19 frontend. The lockfile requires a modern Node runtime. |
| `src/VFR.AiEngine` | Python 3.x | FastAPI + gRPC + Celery service packaged under `vfr_ai_engine`. The interpreter version is not pinned in `requirements.txt`. |

## Local Configuration Surface

### AppHost

The Aspire host reads `src/VFR.AppHost/appsettings.Development.json` and also exposes values through user secrets/config. The important keys are:

- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET_NAME`

These values are forwarded into the AI engine containers. Treat them as local-only secrets and avoid committing real credentials.

### Auth Service

`src/VFR.Auth/ApplicationAuth/appsettings.json` currently expects:

- `ConnectionStrings:Connection`
- `SupportedCultures`
- `TelegramApiKey`
- `Stripe:SecretKey`
- `Stripe:WebhookSecret`
- `Stripe:SuccessUrl`
- `Stripe:CancelUrl`

The code also has an email sender that falls back to a mock path unless these keys are supplied:

- `EmailSettings:Host`
- `EmailSettings:Port`
- `EmailSettings:Email`
- `EmailSettings:Password`

### Profile API

The profile service gets its database connection from Aspire and uses Redis via service discovery. Studio avatar-generation tasks are tracked in Redis outside `Testing`, with in-memory tracking retained for integration tests.

Important keys:

- `AiEngine:BaseUrl` / `AI_ENGINE_BASE_URL` for server-to-server enqueue/status calls.
- `AiEngine:PublicBaseUrl` / `AI_ENGINE_PUBLIC_BASE_URL` for converting AI `/models/...` artifacts into browser-fetchable URLs. AppHost sets this to the AI engine HTTP endpoint for local dev.

JWT validation material is still partly hardcoded in code. That should be externalized before this is treated as production-ready.

### AI Engine

The AI service consumes environment variables directly. Runtime entrypoints are `python -m vfr_ai_engine.api.main` for FastAPI/gRPC and `celery -A vfr_ai_engine.tasks.app.celery_app worker --loglevel=info --pool=solo` for the worker. See `src/VFR.AiEngine/.env.example` for the supported local keys. The important ones are:

- `REDIS_URL`
- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET_NAME`
- `AVATAR_STORAGE_BASE`
- `AVATAR_STORAGE_DIR`
- `GARMENT_STORAGE_DIR`
- `AI_ENGINE_ALLOWED_ORIGINS`
- `PORT`
- `GRPC_PORT`
- `OMP_NUM_THREADS`
- `RUN_WORKER`

### Frontend

The web client reads Vite env variables from `src/vfr-web/.env` or the Aspire-injected process environment:

- `VITE_AUTH_API_URL`
- `VITE_PROFILE_API_URL`
- `VITE_AI_ENGINE_API_URL` for legacy/direct AI surfaces only; Studio generation should flow through Profile API.

The current local `.env` only sets the auth and profile URLs, so the AI engine URL falls back to `http://localhost:8000` unless it is provided explicitly.

## Current Drift Risks

- The solution mixes .NET 9 services with a .NET 8 auth subtree. That is workable, but it means local SDK setup has to be deliberate.
- Profile API still contains hardcoded JWT validation material. That is a security and maintainability risk.
- Startup database migrations happen inside service startup code. That is convenient for local dev, but it is fragile for repeatable deployments.
- Studio avatar generation is brokered through ProfileApi, which calls the AI engine over HTTP. Keep direct browser-to-AI calls out of the Studio generation path.
- Secrets and local credentials are currently scattered across `appsettings.Development.json` and `.env` files. They should be kept local and replaced with documented secret handling for any shared environment.
- There is no real automated test suite yet, so changes in auth/profile/AI boundaries are easy to regress.

## Suggested Local Entry Point

For day-to-day development, the most representative entry point is:

```powershell
dotnet run --project src/VFR.AppHost/VFR.AppHost.csproj
```

That gives you the service composition the repository currently assumes.
