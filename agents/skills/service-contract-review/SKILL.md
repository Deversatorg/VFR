---
name: service-contract-review
description: Review cross-service request/response contracts between vfr-web, ProfileApi, Auth, and AiEngine. Use when data shapes or ownership boundaries change.
---

# Service Contract Review

Do NOT use this skill when:

- the change is within a single service with no cross-boundary effects → use the domain-specific review skill
- the goal is ProfileApi-specific draft/hash logic → use `profile-api-contract-review`

Read the root `CONTEXT.md` and the nearest slice contexts first.

Map each affected shape by:

- owner
- producer
- consumer
- persistence location
- auth boundary

Apply the current repo boundaries:

- `VFR.ProfileApi` owns persisted profile and Studio draft state.
- `VFR.ProfileApi` stores generated-avatar metadata, but not AI enqueue.
- `vfr-web` still calls `VFR.AiEngine` directly for avatar generation.
- `VFR.Auth` owns identity and token issuance.

## Risks

- DTO changes without matching frontend or backend updates
- status-polling payload drift
- generated-avatar metadata no longer matching persisted draft assumptions
- token propagation or auth requirements changing silently
- env-var or base-URL changes that break one side of the boundary
- ownership changes happening implicitly in code without docs or tests

Require at least one verification step on each affected side of the contract.
