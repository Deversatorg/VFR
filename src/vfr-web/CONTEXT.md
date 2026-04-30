# vfr-web Context

Updated: 2026-03-21

## Role

This is the active frontend for the virtual fitting room. Treat this as the real web app. `src/VFR.Web` is not in active use.

## Entry points

- `src/App.tsx` defines the route tree.
- `src/api/apiClients.ts` defines the HTTP clients and env fallbacks.
- `src/pages/studio/Studio.tsx` contains the core studio/avatar flow.
- `src/components/studio/studioState.ts` contains Studio draft, generated-avatar, and fingerprint helpers.

## Main dependencies

- React 19
- Vite 7
- TypeScript 5.9
- React Router 7
- Zustand
- Three.js / React Three Fiber / Drei
- Tailwind 4

## Live integration shape

- Auth requests go to `VITE_AUTH_API_URL`.
- Profile requests go to `VITE_PROFILE_API_URL`.
- Avatar generation requests go to the Profile API broker.
- The profile client injects the bearer token.
- Studio persists draft state through the Profile API and enqueues/polls avatar generation through the Profile API broker.

## Current issues

- Browser code should no longer shape AI generation payloads directly; keep the Profile API broker as the browser-facing boundary.
- There is no browser E2E suite yet.
- The legacy AI client still exists for older surfaces; Studio generation should not depend on `VITE_AI_ENGINE_API_URL`.
- The frontend owns draft-fingerprint logic for local dirty/current UX, while ProfileApi owns generated-avatar persistence.
- Studio now has separate saved-draft and generated-avatar state, which is better UX but also easier to desynchronize if either backend changes shape.

## Open next

- `src/App.tsx`
- `src/api/apiClients.ts`
- `src/pages/studio/Studio.tsx`
- `src/components/studio/studioState.ts`
- `../VFR.ProfileApi/CONTEXT.md`
- `../VFR.AiEngine/CONTEXT.md`
