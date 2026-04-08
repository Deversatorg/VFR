# Code Review

Use this command for findings-first review of changes in this repository.

## Workflow

1. Review for bugs, behavioral regressions, security risks, and missing tests first.
2. Identify the owner of each changed contract or persistence shape.
3. Check whether tests still match current `Testing` startup behavior.
4. Check whether env/config fallbacks could hide a broken deployment.
5. Prefer a small number of high-confidence findings over broad style commentary.

## Repo-Specific Focus

- `vfr-web` direct dependency on AI engine URLs and payload shapes
- `VFR.ProfileApi` draft persistence and generated-avatar metadata
- `VFR.Auth` JWT/billing/admin side effects
- `VFR.AiEngine` queue/status contracts, artifact paths, and fallback uploads
- `VFR.AppHost` service discovery and config wiring

## Output

Return findings ordered by severity with:

- title
- file and line
- impact
- why it matters in this repo

Keep summaries brief and secondary.
