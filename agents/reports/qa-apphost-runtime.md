# AppHost Runtime QA Report

## Findings

- P1 - AppHost runtime graph starts, but Auth account endpoints fail and block deep E2E.
  - File/line: `src/VFR.Auth/ApplicationAuth/Features/Account/Register/RegisterHandler.cs:38`, `src/VFR.Auth/ApplicationAuth/Features/Account/Login/LoginHandler.cs:33`
  - Owner: `VFR.Auth`
  - Impact: The full local Aspire environment cannot complete authenticated scenarios even though AppHost itself builds and services become reachable.
  - Reproduction:
    - Run `dotnet run --project src/VFR.AppHost/VFR.AppHost.csproj`.
    - Confirm services are reachable.
    - POST to Auth `/api/v1/users` or `/api/v1/sessions`.
    - Actual: HTTP 500 from both account endpoints.

## Scope

- Checked `src/VFR.AppHost` build, Aspire runtime startup, container graph, AI Engine/worker/Redis/Postgres/pgAdmin containers, service reachability, frontend Vite service, ProfileApi health, Auth health/plans, and AI health.

## Commands Run

- `dotnet build src/VFR.AppHost/VFR.AppHost.csproj`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS.
- `dotnet run --project src/VFR.AppHost/VFR.AppHost.csproj`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for startup.
  - Notes: Aspire dashboard listened on `https://localhost:17177`; runtime generated an ephemeral development JWT signing key.
- `docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS.
  - Notes: AI Engine, AI worker, Redis, Postgres, and pgAdmin containers were running.
- `curl http://127.0.0.1:55077/health`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for AI Engine health.
- `curl http://127.0.0.1:54811/health`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for ProfileApi health.
- `curl http://127.0.0.1:54809/health`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for Auth health.
- `curl http://127.0.0.1:55086/`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for frontend root HTML.
- `docker stop ...`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS cleanup of QA containers left by AppHost shutdown.

## E2E Scenarios

- Aspire graph build
  - Input state: Current working tree.
  - Expected: AppHost compiles.
  - Actual: PASS.

- Aspire graph startup
  - Input state: Docker available.
  - Expected: Auth, ProfileApi, frontend, AI Engine, AI worker, Redis, and Postgres start.
  - Actual: PASS.

- Service reachability
  - Input state: AppHost running.
  - Expected: Health endpoints and frontend root respond.
  - Actual: PASS for Auth, ProfileApi, AI Engine, and frontend root.

- Redis-backed profile generation tracking outside `Testing`
  - Input state: Authenticated ProfileApi generation request.
  - Expected: Runtime Redis-backed tracker is used.
  - Actual: BLOCKED because Auth account endpoints failed before a token could be obtained.

- Generated artifact browser/network check
  - Input state: Successful AI job.
  - Expected: `/models/...` or `/models/garments/...` artifact URL fetches through runtime.
  - Actual: BLOCKED by Auth/generation flow failure.

## Residual Test Gaps

- Full authenticated browser E2E was not completed because Auth register/login returned 500.
- Browser automation tooling was absent, so no viewport, console, or interactive AppHost dashboard/browser pass was completed.
- Request-level child service logs for Auth 500s were not captured through AppHost stdout/stderr in this run.

## Assumptions

- AppHost ports were dynamic for this run: Auth `54809`, ProfileApi `54811`, AI Engine `55077`, frontend `55086`.
- QA-created AppHost processes and containers were stopped after the run.
- No extra git branches were included; "all branches" was interpreted as all project service areas in the current working tree.
