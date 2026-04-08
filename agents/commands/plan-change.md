# Plan Change

Use this command before non-trivial work that spans multiple files or services.

## Workflow

1. Restate the requested outcome in repo terms.
2. Read the nearest `CONTEXT.md` files and identify the owning boundary.
3. Name the affected slices explicitly: `vfr-web`, `VFR.ProfileApi`, `VFR.Auth`, `VFR.AiEngine`, `VFR.AppHost`.
4. Split the work into implementation, contract, and verification steps.
5. Call out hidden risks:
   - cross-service DTO drift
   - auth/token assumptions
   - AppHost/config wiring
   - expensive AI-path verification gaps
6. Propose the minimum verification matrix needed after the change.

## Output

Return a short plan with:

- goal
- affected slices
- ordered steps
- risks
- verification
