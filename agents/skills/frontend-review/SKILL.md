---
name: frontend-review
description: Review React/TypeScript code, API integration, and Studio state in vfr-web. Use for code quality, contract drift, and frontend coding standards.
---

# Frontend Review

Do NOT use this skill when:

- the goal is E2E scenario validation or browser-flow testing → use `e2e-validation`
- the change is in backend services → use `dotnet-review` or `ai-engine-review`

Read `src/vfr-web/CONTEXT.md` first.

## Entry Points

- `src/vfr-web/src/api/apiClients.ts`
- `src/vfr-web/src/pages/studio/Studio.tsx`
- `src/vfr-web/src/pages/studio/QuickSetup.tsx`
- `src/vfr-web/src/components/studio/studioState.ts`
- touched auth or route files under `src/vfr-web/src/pages`

## Standards

- Keep API URL and client setup centralized in `apiClients.ts`.
- Preserve the distinction between saved draft state and generated-avatar state.
- Treat Studio fingerprint logic as contract-sensitive code, not casual UI glue.
- Avoid silent localhost fallbacks unless the fallback is intentional and documented.
- Prefer explicit types for API payloads and responses.
- Keep components focused; extract pure helpers before introducing abstraction layers.
- Match existing route and state-management patterns before inventing new ones.

## Risks

- localhost base-URL fallbacks masking missing env wiring
- token injection applied to the wrong clients or missing where needed
- `authClient` exclusions accidentally widening or shrinking authenticated behavior
- `profileClient` and `avatarClient` request payloads drifting from backend expectations
- Studio flow drift across `load profile -> save draft -> generate avatar -> poll status -> persist generated metadata`
- relative `model_url` normalization breaking generated-avatar loading
- browser code depending on AI-engine internals that changed shape
- response-shape changes without matching `studioState.ts` mapping updates

If a frontend change alters a request or response shape, trigger `service-contract-review`.
Require at least one check on both the frontend caller and the backend contract owner when shapes change.
