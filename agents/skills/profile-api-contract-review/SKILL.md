---
name: profile-api-contract-review
description: Review ProfileApi persistence and Studio draft contracts. Use when profile, draft hash, measurement, or generated-avatar metadata shapes change.
---

# Profile API Contract Review

Do NOT use this skill when:

- the change spans multiple services → use `service-contract-review`
- the goal is auth security or JWT review → use `auth-security`

Read these first:

- `src/VFR.ProfileApi/CONTEXT.md`
- root `CONTEXT.md`

## Entry Points

- `src/VFR.ProfileApi/Program.cs`
- `src/VFR.ProfileApi/Features/GetProfile/GetProfileEndpoint.cs`
- `src/VFR.ProfileApi/Features/GetProfile/GetProfileResponse.cs`
- `src/VFR.ProfileApi/Features/UpsertStudioProfile/UpsertStudioProfileEndpoint.cs`
- `src/VFR.ProfileApi/Features/UpsertStudioProfile/UpsertStudioProfileRequest.cs`
- `src/VFR.ProfileApi/Features/UpsertStudioProfile/UpsertStudioProfileHandler.cs`
- `src/VFR.ProfileApi/Features/Studio/StudioDraftStateHasher.cs`
- touched integration tests in `tests/VFR.ProfileApi.IntegrationTests`

## Risks

- `draftStateHash` no longer matching the frontend fingerprint assumptions
- `generatedAvatar`, `lastAvatarModelUrl`, or `inputHash` semantics drifting from Studio expectations
- persistence-only metadata logic quietly turning into enqueue ownership
- nullable measurement handling changing browser save behavior
- enum or casing changes breaking `toBodyTypeEnum` or `toGenderEnum` assumptions in the frontend
- `Testing` startup behavior, JWT config, or bootstrap control no longer matching tests
- response-shape changes without matching `StudioProfileResponse` updates

Treat this service as the source of truth for persisted Studio state, not for AI job orchestration.
