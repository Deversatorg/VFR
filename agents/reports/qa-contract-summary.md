# Contract Checker QA Summary

## Findings

- P1 - Cross-service authenticated E2E is blocked by Auth runtime 500s.
  - File/line: `src/VFR.Auth/ApplicationAuth/Features/Account/Register/RegisterHandler.cs:38`, `src/VFR.Auth/ApplicationAuth/Features/Account/Login/LoginHandler.cs:33`
  - Impact: Producer/consumer contracts for authenticated Studio, ProfileApi broker, and AI generation cannot be fully proven in the live AppHost environment because the token-producing Auth paths fail first.
  - Reproduction: Under AppHost, `POST /api/v1/users` and `POST /api/v1/sessions` returned HTTP 500.

- P3 - EF Core Relational package warning appears in ProfileApi-related test output.
  - File/line: test/build output
  - Impact: Non-blocking dependency drift warning; keep an eye on runtime differences between isolated tests and AppHost.
  - Reproduction: Run ProfileApi integration tests or ApiFlow tests with normal verbosity.

## Scope

- Final contract pass across `vfr-web`, `VFR.ProfileApi`, `VFR.Auth`, `VFR.AiEngine`, `VFR.AppHost`, tests, docs/agent command references, runtime service discovery, and package-refactor assumptions.

## Commands Run

- `dotnet build src/VFR.AppHost/VFR.AppHost.csproj`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS.
- `dotnet test tests/VFR.ProfileApi.IntegrationTests/VFR.ProfileApi.IntegrationTests.csproj --logger "console;verbosity=normal"`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 10/10 tests.
- `dotnet test tests/ApplicationAuth.IntegrationTests/ApplicationAuth.IntegrationTests.csproj --logger "console;verbosity=normal"`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 6/6 tests.
- `dotnet test tests/VFR.ApiFlowTests/VFR.ApiFlowTests.csproj --logger "console;verbosity=normal"`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 1/1 tests.
- `& 'C:\Program Files\nodejs\npm.cmd' run build`
  - Cwd: `C:\projects\virtual-fitting-room\src\vfr-web`
  - Result: PASS.
- `& 'C:\Program Files\nodejs\npm.cmd' run lint`
  - Cwd: `C:\projects\virtual-fitting-room\src\vfr-web`
  - Result: PASS.
- `docker build -t vfr-aiengine-qa .`
  - Cwd: `C:\projects\virtual-fitting-room\src\VFR.AiEngine`
  - Result: PASS.
- `docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v C:\projects\virtual-fitting-room:/repo -w /repo/src/VFR.AiEngine vfr-aiengine-qa python -m unittest discover -s tests -v`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 17/17 tests.
- `docker run --rm vfr-aiengine-qa python -m vfr_ai_engine.tools.generate_protos`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS.
- `dotnet run --project src/VFR.AppHost/VFR.AppHost.csproj`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for graph startup; FAIL for full authenticated E2E because Auth account endpoints returned 500.

## E2E Scenarios

- Static HTTP AI route contract
  - Expected: Routes unchanged.
  - Actual: PASS. Verified:
    - `POST /api/v1/avatar/generate`
    - `POST /api/v1/avatar/generate-from-profile`
    - `GET /api/v1/avatar/status/{task_id}`
    - `POST /api/v1/garment/generate`
    - `GET /api/v1/garment/status/{task_id}`

- Celery task names
  - Expected: Names unchanged.
  - Actual: PASS. Verified:
    - `generate_3d_avatar`
    - `generate_3d_avatar_from_profile`
    - `generate_garment_3d`

- Artifact URL contract
  - Expected: Avatar local fallback returns `/models/...`; garment returns `/models/garments/...`; ProfileApi accepts/normalizes AI model URLs.
  - Actual: PASS by AI unit tests/static checks for local fallback and by ProfileApi contract shape. Runtime browser fetch of a newly generated artifact was blocked before generation could be queued.

- Generated avatar/profile metadata
  - Expected: Result metadata includes `model_url`, `measurements`, `targets`, and `measurement_sources`.
  - Actual: PASS in AI task/pipeline and ProfileApi `AiAvatarStatusResult`.

- gRPC legacy isolation
  - Expected: gRPC surface exists only for legacy compatibility and does not become the active ProfileApi path.
  - Actual: PASS. Static search found gRPC usage in AI Engine server/tests only; ProfileApi uses HTTP AI client.

- `Testing` startup lightweight behavior
  - Expected: Integration tests avoid real PostgreSQL/Redis where replacements are configured.
  - Actual: PASS for ProfileApi/Auth/API flow suites.

- Docs/agent command path drift
  - Expected: Docs and agent references use current package paths, not deleted root Python entrypoints.
  - Actual: PASS for searched references. Matches were current package paths such as `vfr_ai_engine/api/main.py`, not old root `main.py` startup commands.

## Residual Test Gaps

- Full browser E2E, responsive checks, and console-error scans were not run because Playwright/browser tooling was unavailable locally.
- Authenticated Studio/ProfileApi/AI generation flow is not proven in AppHost until Auth register/login 500s are fixed.
- Full SMPL-X generation and real S3 upload were not run in local QA.
- Password reset and email verification remain partial because local SMTP is not configured and registration failed.
- Runtime Redis generation tracking was not exercised with a successful authenticated generation request.

## Assumptions

- Reports cover all project service areas in the current working tree rather than all git branches.
- AppHost dynamic ports were discovered at runtime and are not stable.
- Docker is an acceptable fallback for AI checks when host Python is missing.
- Existing dirty worktree changes outside these QA reports and the proto-helper fix are treated as user/refactor-owned.
