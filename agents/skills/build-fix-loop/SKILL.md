---
name: build-fix-loop
description: Diagnose and fix build or test failures with a reproduce-isolate-fix-verify loop. Use when dotnet, frontend, or Python checks fail.
---

# Build Fix Loop

Do NOT use this skill when:

- the goal is code review or security analysis → use the appropriate review skill
- nothing is failing; you are doing proactive review

Start with the narrowest failing command.

## Loop

1. Reproduce the failure exactly.
2. Decide whether it is build, test, startup, config, or contract related.
3. Isolate the smallest likely root cause.
4. Fix only that root cause.
5. Re-run the exact failing command.
6. Widen verification only if the changed boundary demands it.

## Repo-Aware Routing

- `src/vfr-web`: `npm run build`, then `npm run lint`
- `src/VFR.ProfileApi`: targeted integration test project
- `src/VFR.Auth`: targeted integration test project
- `src/VFR.AppHost`: build when service graph or config wiring changed
- `src/VFR.AiEngine`: `python -m py_compile ...` before deeper runtime debugging

## Common False Leads

- known EF Core package-version warnings that are noisy but not root cause
- local env fallbacks masking broken config
- test-only startup code being changed accidentally
- frontend and AI payload drift presenting as unrelated runtime failures
