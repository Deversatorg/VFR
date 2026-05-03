---
name: ai-engine-security
description: Find security risks in VFR.AiEngine — inputs, paths, storage, CORS, artifact exposure. Use for exploit-focused review of Python, FastAPI, and S3 code.
---

# AI Engine Security

Do NOT use this skill when:

- the goal is code quality, contract correctness, or ML accuracy → use `ai-engine-review`
- the change is in .NET auth code → use `auth-security`

Read these first:

- `src/VFR.AiEngine/CONTEXT.md`
- `agents/references/ai-engine-trust-boundaries.md`

## Entry Points

- `src/VFR.AiEngine/vfr_ai_engine/runtime/api`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/tasks`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/storage/s3_client.py`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/avatar/pipeline.py`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/garments/pipeline.py`
- `src/VFR.AiEngine/tests/test_status_endpoints.py`

## Risks

### External Inputs

- CORS admitting broader origins than intended
- queue endpoints accepting abusive or weakly validated payloads
- missing request validation or type coercion issues
- path traversal or unsafe path joins from user-controlled identifiers
- unsafe deserialization or implicit trust in model artifacts
- `torch.load` or pickle-based loading of untrusted files

### Storage and Artifacts

- local-path fallback returning filesystem paths to callers or upstream services
- public URL construction not matching the real storage exposure model
- temporary upload files persisting longer than expected
- generated garment or avatar artifacts being written into overly broad static directories
- cleanup routines failing silently and leaving stale user artifacts behind
- user-controlled identifiers shaping bucket keys or filenames without normalization

### Leakage

- task status endpoints leaking internal errors, filesystem paths, or sensitive metadata
- worker task contracts drifting from HTTP response assumptions
- logs exposing absolute paths, storage endpoints, or internal filenames unnecessarily
- secrets leaking through logs, exceptions, or response payloads
- temporary upload paths becoming observable or reusable by the wrong caller
- local artifact URLs being returned where public URLs are expected

Prefer fixes that add validation, narrow trust, and add a regression test near the affected path.
Separate contract-security issues from model-quality issues.
