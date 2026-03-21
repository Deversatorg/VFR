# VFR.ApiFlowTests Context

Updated: 2026-03-21

## Role

API-level happy-path tests across auth, profile, and AI enqueue boundaries.

## What this project is supposed to prove

- register and confirm a user in auth
- log in and obtain a bearer token
- use that token against profile API
- save studio profile data
- shape and send the AI enqueue request

## Important files

- `ApiHappyPathTests.cs`
- `ApplicationAuthFlowFactory.cs`
- `ProfileApiJwtFlowFactory.cs`
- `AiEnqueueTestServer.cs`

## Current state

- This project passed on 2026-03-21.
- It depends on both auth and profile test startup behavior staying compatible with `WebApplicationFactory`.
- If it starts failing again, verify the auth host first because that is the earliest point in the flow.

## Extra note

- This project also emits the EF Core Relational 9.0.2 vs 9.0.3 warning.
- Running it in parallel with the other .NET test projects can cause file-lock failures on shared build outputs. Prefer sequential runs.

## Open next

- `ApplicationAuthFlowFactory.cs`
- `ApiHappyPathTests.cs`
- `../../src/VFR.Auth/ApplicationAuth/CONTEXT.md`
- `../../src/VFR.ProfileApi/CONTEXT.md`
