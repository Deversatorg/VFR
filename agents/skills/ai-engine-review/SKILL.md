---
name: ai-engine-review
description: Review FastAPI, Celery, and PyTorch/SMPL-X code in VFR.AiEngine. Use for correctness, contract, and performance issues in the generation pipeline.
---

# AI Engine Review

Do NOT use this skill when:

- the goal is finding security exploits, path traversal, or storage exposure → use `ai-engine-security`
- the change is in .NET services → use `dotnet-review`

Read `src/VFR.AiEngine/CONTEXT.md` first.

## Entry Points

- `src/VFR.AiEngine/vfr_ai_engine/api`
- `src/VFR.AiEngine/vfr_ai_engine/tasks`
- `src/VFR.AiEngine/vfr_ai_engine/avatar/pipeline.py`
- `src/VFR.AiEngine/vfr_ai_engine/measurements`
- `src/VFR.AiEngine/vfr_ai_engine/storage/s3_client.py`
- `src/VFR.AiEngine/vfr_ai_engine/garments/pipeline.py`
- relevant files in `src/VFR.AiEngine/tests`

## Risks

### API and Worker Contracts

- request/response drift on `generate-from-profile` and status polling endpoints
- task identifiers or result payloads that no longer match frontend expectations
- blocking or expensive work accidentally moved into the HTTP request path
- local-path fallback behavior masking missing S3 credentials or deployment bugs
- temporary file, artifact, or upload cleanup gaps
- placeholder proxy-loop behavior becoming user-visible without clear metadata
- heavy ML-path changes with no narrow helper or contract tests

### PyTorch and Inference

- trusted versus untrusted model artifact loading
- missing `no_grad` or inference-only execution where it matters
- device-placement mistakes and silent CPU/GPU mismatches
- shape, dtype, or normalization errors that corrupt measurements
- memory blowups from unnecessary tensor copies
- non-deterministic or weakly explained proxy-target fitting changes
- placeholder shoulder, bicep, or thigh loops leaking into user-facing outputs without metadata

Separate three kinds of issues: security/trust, deterministic correctness, and model-quality limitations.
Distinguish code defects from model-quality limitations. Prefer concrete contract or correctness findings.
