# Build Fix

Use this command when the repo does not build, tests fail, or a service stops starting after a change.

## Workflow

1. Reproduce the failure with the narrowest relevant command.
2. Identify whether the failure is in:
   - frontend build/lint
   - .NET compile/test
   - AppHost wiring
   - Python syntax/runtime setup
   - cross-service contract drift
3. Fix the smallest root cause first.
4. Re-run the exact failing command.
5. Expand verification only to the affected boundary.

## Repo-Specific Checks

- Build AppHost when startup wiring or service references changed:
  `dotnet build src/VFR.AppHost/VFR.AppHost.csproj`
- Run .NET tests sequentially, never in parallel in this repo.
- Use the slice-specific integration test project before broadening to `VFR.ApiFlowTests`.
- For `src/vfr-web`, run `npm run build` and `npm run lint`.
- For `src/VFR.AiEngine`, run `python -m compileall vfr_ai_engine` before chasing deeper runtime issues.

## Output

Report:

- failing command
- root cause
- fix
- verification run
- residual risk
