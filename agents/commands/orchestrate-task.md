# Orchestrate Task

Use this command when the work spans more than one service or benefits from parallel contributors.

## Workflow

1. Split the task by ownership boundary, not by file count.
2. Assign one clear write scope per worker.
3. Keep one reviewer or contract-checker read-only.
4. Merge slices only after each worker states:
   - files touched
   - verification run
   - assumptions made
5. Finish with a cross-service contract pass if more than one slice changed.

## Suggested Split

- `frontend-worker`: `src/vfr-web`
- `dotnet-api-worker`: `src/VFR.ProfileApi`
- `auth-worker`: `src/VFR.Auth`
- `python-ai-worker`: `src/VFR.AiEngine`
- `contract-checker`: read-only cross-service review

## Guardrails

- Do not duplicate work between workers.
- Do not move ownership across services without an explicit decision.
- Do not merge a payload shape change without checking every producer and consumer.
