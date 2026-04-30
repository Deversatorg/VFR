# VFR.AiEngine Context

Updated: 2026-04-27

## Role

Python service for avatar and garment generation. It exposes FastAPI HTTP endpoints, starts a gRPC server, and pushes heavy work to Celery workers backed by Redis.

## Entry points

- `vfr_ai_engine/api/main.py` for FastAPI startup and in-process gRPC bootstrap
- `vfr_ai_engine/tasks/app.py` for Celery app configuration
- `vfr_ai_engine/tasks/avatar.py` and `vfr_ai_engine/tasks/garments.py` for Celery task handlers
- `vfr_ai_engine/avatar/pipeline.py` and `vfr_ai_engine/garments/pipeline.py` for generation logic
- `vfr_ai_engine/measurements/optimizer.py`, `anthropometry.py`, and `proxy_targets.py` for measurement math
- `vfr_ai_engine/storage/s3_client.py` for S3-compatible upload behavior
- `Dockerfile` for container build and proto generation

## Active runtime path

- The current live path used by ProfileApi is HTTP:
- `POST /api/v1/avatar/generate-from-profile`
- `GET /api/v1/avatar/status/{task_id}`
- Profile-based generation now returns `model_url`, measured outputs, optimizer targets, and measurement-source metadata for Studio refinement.
- Local artifact fallbacks must return FastAPI-served `/models/...` paths, never container temp paths.
- Garment artifacts use `GARMENT_STORAGE_DIR`; AppHost mounts the same directory into FastAPI and worker containers so `/models/garments/...` can serve worker-generated GLBs.
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
- If S3 credentials are missing, uploads fall back to the FastAPI-served `/models/...` path.
- There is an older `ai_context.md` in this folder. Treat it as potentially stale and prefer this file plus the code.

## Open next

- `vfr_ai_engine/api`
- `vfr_ai_engine/tasks`
- `vfr_ai_engine/avatar`
- `vfr_ai_engine/measurements`
- `vfr_ai_engine/storage`
- `tests/test_status_endpoints.py`
- `tests/test_proxy_targets.py`
