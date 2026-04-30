# Auth QA Report

## Findings

- P1 - AppHost runtime Auth register and login endpoints return HTTP 500.
  - File/line: `src/VFR.Auth/ApplicationAuth/Features/Account/Register/RegisterHandler.cs:38`, `src/VFR.Auth/ApplicationAuth/Features/Account/Login/LoginHandler.cs:33`
  - Owner: `VFR.Auth`
  - Impact: This blocks every authenticated E2E flow: registration, login/logout/login-again, Quick Setup, Studio, generated avatar, protected billing, and admin checks. Integration tests pass, so the failure is specific to the non-`Testing` AppHost runtime path.
  - Reproduction:
    - Start `dotnet run --project src/VFR.AppHost/VFR.AppHost.csproj`.
    - Call Auth runtime `POST /api/v1/users` with a new email/password payload.
    - Call Auth runtime `POST /api/v1/sessions` with the default QA/admin credentials attempted in this run.
    - Actual result: both returned HTTP 500 problem responses.
  - Why it matters: The first handler DB access points are at the referenced lines, and the service health/plans endpoints were reachable, so the regression appears in account-command execution rather than process startup.

- P3 - Local email delivery is not configured.
  - Route: registration/email confirmation flow
  - Impact: Email confirmation and password reset can only be validated as far as local mock/skip behavior allows. This is expected in local dev, but it limits deep E2E coverage of verification/reset links.
  - Reproduction: Auth integration tests pass while logging that SMTP settings are incomplete and delivery is skipped.

## Scope

- Checked `src/VFR.Auth` integration suite, runtime health, billing plans, swagger availability, registration/login endpoints, and auth-dependent project flows.
- Reviewed account handler failure surface for register/login runtime failures.

## Commands Run

- `dotnet test tests/ApplicationAuth.IntegrationTests/ApplicationAuth.IntegrationTests.csproj --logger "console;verbosity=normal"`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 6/6 tests.
- `curl http://127.0.0.1:54809/health`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, returned `Healthy`.
- `curl http://127.0.0.1:54809/api/v1/plans`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, returned Basic and Pro plans.
- `curl http://127.0.0.1:54809/api/v1/users`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS for route existence, returned 405 to GET with POST allowed.
- `curl -X POST http://127.0.0.1:54809/api/v1/users ...`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: FAIL, returned HTTP 500.
- `curl -X POST http://127.0.0.1:54809/api/v1/sessions ...`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: FAIL, returned HTTP 500.

## E2E Scenarios

- Register new user
  - Input state: AppHost runtime, unique QA email.
  - Expected: User is created or receives validation/confirmation response.
  - Actual: FAIL, HTTP 500.

- Login existing/default user
  - Input state: AppHost runtime, default QA/admin credential attempt.
  - Expected: Token response or validation error.
  - Actual: FAIL, HTTP 500.

- Forgot/reset password
  - Input state: Local runtime with no SMTP.
  - Expected: Flow proceeds as far as configured local email/mock behavior allows.
  - Actual: BLOCKED by inability to establish a working account session; full email loop also limited by missing SMTP config.

- Email verification
  - Input state: Registration should create confirmation code/link.
  - Expected: Local flow reaches confirmation boundary.
  - Actual: BLOCKED by register 500; email delivery is also skipped locally.

- Billing/public plans
  - Input state: Unauthenticated runtime.
  - Expected: Plans endpoint returns available plans.
  - Actual: PASS.

## Residual Test Gaps

- Token refresh, logout, admin, reset-password, and verification-link happy paths were not exercised because register/login failed first.
- Root-cause logs for the 500s were not surfaced by AppHost stdout/stderr during this run; child service request logs need collection or structured logging attachment.

## Assumptions

- Runtime Auth port for this AppHost run was `54809`.
- SMTP absence is an environment limitation, not a functional regression by itself.
- The account 500 is treated as high severity because it blocks cross-service E2E, even though isolated Auth integration tests pass.
