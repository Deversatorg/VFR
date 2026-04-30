# Frontend QA Report

## Findings

- P1 - Runtime authenticated browser flows are blocked by Auth 500s, not by a confirmed frontend defect.
  - Owner: `VFR.Auth`
  - Impact: Register/login, Quick Setup, Studio, billing protected routes, and avatar generation UX cannot be completed end-to-end through the browser in the AppHost runtime because the frontend cannot obtain an access token.
  - Reproduction: start `dotnet run --project src/VFR.AppHost/VFR.AppHost.csproj`, then call Auth `POST /api/v1/users` or `POST /api/v1/sessions`; both returned HTTP 500 during this QA run.
  - Frontend route impact: all protected `src/vfr-web` flows that depend on authenticated API calls.

- P3 - Production bundle is very large.
  - File/route: `src/vfr-web` Vite build output
  - Impact: The main generated JS chunk was reported at about 1.65 MB uncompressed and 475 KB gzip. This is not a functional failure, but it can slow first load and hide performance regressions in user-visible flows.
  - Reproduction: run `npm.cmd run build` from `src/vfr-web`; Vite emits the chunk-size warning.

## Scope

- Checked `src/vfr-web` build and lint health.
- Runtime smoke-tested the Vite-served frontend through AppHost.
- Reviewed frontend participation in auth, protected-route, Studio, generated-avatar, and billing flows at the level possible without a working runtime Auth token.

## Commands Run

- `& 'C:\Program Files\nodejs\npm.cmd' run build`
  - Cwd: `C:\projects\virtual-fitting-room\src\vfr-web`
  - Result: PASS
  - Notes: Vite built successfully; emitted large chunk warning.
- `& 'C:\Program Files\nodejs\npm.cmd' run lint`
  - Cwd: `C:\projects\virtual-fitting-room\src\vfr-web`
  - Result: PASS
- `curl http://127.0.0.1:55086/`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS
  - Notes: AppHost frontend served HTML from Vite.

## E2E Scenarios

- Public page render
  - Input state: AppHost stack running, unauthenticated browser/client.
  - Expected: Frontend root serves without requiring auth.
  - Actual: PASS at HTTP smoke level; browser console checks were not run because Playwright/browser tooling was not installed in this workspace.

- Register new user, login, logout, login again
  - Input state: AppHost stack running.
  - Expected: Frontend can create/login user and establish auth state.
  - Actual: BLOCKED by Auth runtime HTTP 500 on register/login.

- Quick Setup creates a profile and routes into Studio
  - Input state: Authenticated user.
  - Expected: Profile API persists profile, Studio opens with saved state.
  - Actual: BLOCKED because Auth token acquisition failed.

- Studio draft load, dirty edits, save, revert, stale avatar behavior
  - Input state: Authenticated user with profile.
  - Expected: Draft state persists, dirty state is visible, revert does not corrupt persisted profile, draft changes mark generated avatar stale.
  - Actual: BLOCKED by Auth runtime failure. Static/frontend build did not surface compile-time regressions.

- Generate avatar UX
  - Input state: Authenticated user with valid Studio draft and running AI Engine.
  - Expected: Frontend saves draft, requests ProfileApi generation broker, polls status, and displays fetchable `/models/...` artifact URL.
  - Actual: BLOCKED by Auth runtime failure before Studio could be reached with a token.

- Billing and protected routes
  - Input state: Unauthenticated/authenticated states.
  - Expected: Public billing data and protected route handling work without runtime JS errors.
  - Actual: Public backend billing plan endpoint was reachable through Auth; frontend protected-route E2E blocked by Auth token failure.

## Residual Test Gaps

- No real browser automation was completed because Playwright/browser binaries were not installed in the workspace.
- No console-error scan, responsive viewport pass, or click-path validation was completed.
- Studio and billing protected flows remain unverified at browser level until Auth runtime account endpoints stop returning 500.

## Assumptions

- Current local `main` means current working tree/service areas, not every git branch.
- AppHost dynamically assigned frontend port `55086` for this run.
- Frontend verification relied on build/lint and HTTP smoke because authenticated runtime E2E was blocked upstream.
