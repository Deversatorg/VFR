# VFR.AiEngine Context

Updated: 2026-03-21

## Role

Python service for avatar and garment generation. It exposes FastAPI HTTP endpoints, starts a gRPC server, and pushes heavy work to Celery workers backed by Redis.

## Entry points

- `main.py` for FastAPI + gRPC startup
- `worker.py` for Celery tasks
- `ml_pipeline.py` and `garment_pipeline.py` for heavy generation logic
- `measurement_optimizer.py` for SMPL-X beta optimization and measurement loops
- `s3_client.py` for S3-compatible upload behavior
- `Dockerfile` for container build and proto generation

## Active runtime path

- The current live path used by the frontend is HTTP:
- `POST /api/v1/avatar/generate-from-profile`
- `GET /api/v1/avatar/status/{task_id}`
- Profile-based generation now returns `model_url`, measured outputs, optimizer targets, and measurement-source metadata for Studio refinement.
- gRPC exists, but no active .NET consumer was found by code search on 2026-03-20.

## Config surface

- See `.env.example`.
- Important env vars: `REDIS_URL`, `S3_*`, `AI_ENGINE_ALLOWED_ORIGINS`, `PORT`, `GRPC_PORT`, `OMP_NUM_THREADS`.

## Tests

- `tests/test_status_endpoints.py` is a lightweight contract test file.
- `tests/test_proxy_targets.py` covers proxy-slider normalization, derived proxy targets, and proxy measurement exposure.
- `tests/test_proxy_targets.py` passed in the AI container on 2026-03-21.
- Coverage is still strongest around queue contracts and pure helper logic, not end-to-end mesh quality.

## Current issues

- Python version is not pinned even though the dependency set is heavy.
- The ML path is expensive to run and weakly covered by tests.
- Muscle/fat sliders no longer write directly into semantic SMPL betas. They now become proxy shoulder/bicep/thigh targets that the optimizer fits with lower weights than exact chest/waist/hips.
- The shoulder proxy loop is a temporary upper-torso contour, and the bicep/thigh proxy loops still mirror left-side loops until bilateral loops are extracted properly.
- If S3 credentials are missing, uploads fall back to local paths, which can hide deployment issues.
- There is an older `ai_context.md` in this folder. Treat it as potentially stale and prefer this file plus the code.

## Open next

- `main.py`
- `worker.py`
- `ml_pipeline.py`
- `measurement_optimizer.py`
- `s3_client.py`
- `tests/test_status_endpoints.py`
- `tests/test_proxy_targets.py`
