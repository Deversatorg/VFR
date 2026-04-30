# Profile API QA Report

## Findings

- No P0/P1 ProfileApi defects found in the automated and runtime-smoke checks completed in this pass.

- P3 - EF Core package version conflict warning is present in ProfileApi-related builds/tests.
  - File/line: build output for `tests/VFR.ProfileApi.IntegrationTests/VFR.ProfileApi.IntegrationTests.csproj` and `tests/VFR.ApiFlowTests/VFR.ApiFlowTests.csproj`
  - Impact: MSBuild selected `Microsoft.EntityFrameworkCore.Relational` 9.0.2 over 9.0.3. This did not fail tests, but it is dependency drift in a service that owns persisted generated-avatar metadata.
  - Reproduction: run either ProfileApi integration tests or ApiFlow tests with normal console verbosity.

## Scope

- Checked `src/VFR.ProfileApi` integration behavior for profile data, Studio draft persistence, generated-avatar metadata, in-memory `Testing` tracker, and AI broker contracts.
- Runtime-smoke checked ProfileApi health and unauthorized behavior through AppHost.
- Cross-checked AI status result metadata fields consumed by ProfileApi.

## Commands Run

- `dotnet test tests/VFR.ProfileApi.IntegrationTests/VFR.ProfileApi.IntegrationTests.csproj --logger "console;verbosity=normal"`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 10/10 tests.
  - Notes: Required escalation because sandboxed restore/test access hit user NuGet config permissions.
- `dotnet test tests/VFR.ApiFlowTests/VFR.ApiFlowTests.csproj --logger "console;verbosity=normal"`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 1/1 tests.
- `curl http://127.0.0.1:54811/health`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, returned `Healthy`.
- `curl http://127.0.0.1:54811/api/v1/profiles/me`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for unauthenticated contract, returned 401 with Bearer challenge.

## E2E Scenarios

- Testing startup remains lightweight
  - Input state: Integration tests boot ProfileApi in `Testing`.
  - Expected: Tests replace external services and do not require real PostgreSQL/Redis.
  - Actual: PASS, ProfileApi integration suite completed 10/10.

- Profile protected endpoint rejects anonymous users
  - Input state: AppHost runtime, no bearer token.
  - Expected: 401 Bearer challenge.
  - Actual: PASS.

- Studio generated-avatar metadata contract
  - Input state: AI status success payload consumed by ProfileApi broker.
  - Expected: `model_url`, `measurements`, `targets`, and `measurement_sources` remain modeled.
  - Actual: PASS by static contract check in `src/VFR.ProfileApi/Features/StudioAvatarGeneration/AiEngineClient.cs:205`.

- Authenticated Studio draft save/load and avatar persistence
  - Input state: Authenticated user and ProfileApi runtime.
  - Expected: Draft saves manual/auto fields; generated-avatar metadata persists only after valid AI success and current draft hash.
  - Actual: BLOCKED by Auth runtime 500 on token-producing endpoints.

## Residual Test Gaps

- Authenticated ProfileApi runtime E2E could not be completed because Auth register/login returned HTTP 500 under AppHost.
- Redis-backed generation tracking outside `Testing` was not exercised with a successful authenticated generation request.
- Real browser verification of Studio draft state remains blocked by Auth and missing browser automation tooling.

## Assumptions

- ProfileApi runtime port for this AppHost run was `54811`.
- Existing ProfileApi integration tests are the source of truth for `Testing` replacements.
- No direct ProfileApi gRPC consumer was found in static search; ProfileApi continues to use the HTTP AI broker path.
