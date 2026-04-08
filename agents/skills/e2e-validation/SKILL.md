---
name: e2e-validation
description: Validate high-value browser flows and Studio scenarios end-to-end. Use for draft persistence, avatar generation, status polling, and auth-aware flow testing.
---

# E2E Validation

Do NOT use this skill when:

- the goal is code quality review or coding standards → use `frontend-review`
- the change does not affect user-visible flows

Read these first:

- `src/vfr-web/CONTEXT.md`
- `src/VFR.ProfileApi/CONTEXT.md`
- `src/VFR.AiEngine/CONTEXT.md`

## Entry Points

- `src/vfr-web/src/pages/studio/QuickSetup.tsx`
- `src/vfr-web/src/pages/studio/Studio.tsx`
- `src/vfr-web/src/components/studio/studioState.ts`
- `src/VFR.ProfileApi/Features/GetProfile/GetProfileResponse.cs`
- `src/VFR.ProfileApi/Features/UpsertStudioProfile/*`

## Priority Scenarios

- unauthenticated or missing-profile user is redirected into the right setup path
- quick setup persists initial body data and allows Studio to load
- Studio loads saved draft and generated-avatar metadata correctly
- editing body state marks the draft dirty and enables save/revert behavior
- navigation away with dirty state triggers unsaved-change protection
- save draft persists the correct measurements and clears dirty state
- generate avatar saves the draft first, queues AI generation, polls status, and persists returned metadata
- generated avatar becomes stale when the draft changes and Studio falls back to preview mode
- generate success with metadata-persist failure surfaces a partial-failure message without losing the generated model
- timeout or AI failure leaves the UI in a recoverable state

## General Flow Checks

- app boot and routing
- auth-aware API calls and error handling
- missing-env or broken-endpoint behavior

Prefer stable selectors and deterministic assertions over snapshot-heavy tests.

When a change touches AI generation or draft persistence, pair browser checks with a service contract review.

Before deeper E2E work, run from `src/vfr-web`:

- `npm run build`
- `npm run lint`

Use `agents/templates/studio-e2e-checklist.md` to record which scenarios were covered.
