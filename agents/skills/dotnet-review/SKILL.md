---
name: dotnet-review
description: Review and verify .NET code across ProfileApi, Auth, and AppHost. Use for code quality, regressions, startup, config, and test-harness correctness.
---

# Dotnet Review

Do NOT use this skill when:

- the goal is to find auth exploits, JWT bypass, or payment security issues → use `auth-security`
- the change is only in `src/vfr-web` or `src/VFR.AiEngine`

Read the nearest `CONTEXT.md` first.

## Entry Points

- `src/VFR.ProfileApi/Program.cs`
- `src/VFR.Auth/ApplicationAuth/Program.cs`
- `src/VFR.Auth/ApplicationAuth/DatabaseBootstrapControl.cs`
- `src/VFR.AppHost/Program.cs`
- touched feature, DAL, or test files
- touched files under `Features/Account`, `Features/AdminUsers`, `Features/Payments`, `Features/Telegram`
- related integration tests

## Risks

- `Testing` environment behavior drifting from integration-test assumptions
- JWT config drift between auth, profile, and tests
- startup migrations, bootstrap admin, role seeding, or plan seeding running when they should be disabled
- `.NET 8` and `.NET 9` assumptions crossing slice boundaries
- Aspire service-discovery or config wiring regressions
- DTO or persistence-shape changes without matching consumer updates
- dangerous test endpoints becoming reachable without tight gating
- feature-local Telegram contract changes not propagated to handlers, serializer context, and endpoints together

## Verification

Select the narrowest check that covers the changed boundary:

- AppHost or service wiring:
  `dotnet build src/VFR.AppHost/VFR.AppHost.csproj`
- Profile API changes:
  `dotnet test tests/VFR.ProfileApi.IntegrationTests/VFR.ProfileApi.IntegrationTests.csproj --no-restore`
- Auth changes:
  `dotnet test tests/ApplicationAuth.IntegrationTests/ApplicationAuth.IntegrationTests.csproj --no-restore`
- Cross-service flow changes:
  `dotnet test tests/VFR.ApiFlowTests/VFR.ApiFlowTests.csproj --no-restore`

Run .NET test projects sequentially in this repository.

Separate warnings from failures. The known EF Core relational version warning is not automatically the root cause.

Prefer findings about behavior and risk over style. Call out missing tests when a change touches startup, auth, persistence, or inter-service contracts.
