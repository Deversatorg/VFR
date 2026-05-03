# VFR AiEngine Package Layout

This package is split by whether code participates in the live service path.

## `runtime/`

Runtime code is imported by FastAPI, Celery workers, or avatar/garment generation.

- `api/` exposes HTTP routes, status normalization, middleware, and static GLB mounts.
- `tasks/` owns Celery app setup and task handlers.
- `avatar/` orchestrates profile/avatar generation.
- `garments/` creates garment GLB artifacts.
- `measurements/` contains target inference, optional regressor inference, SMPL-X measurement loops, optimization, and warp code.
- `storage/` writes generated assets to S3 or local `/models` storage.
- `observability/` configures request/task logging context.
- `grpc/` hosts the legacy gRPC surface.
- `paths.py` centralizes runtime filesystem paths.

## `non_runtime/`

Non-runtime code is tooling. It can import runtime helpers for validation, but runtime code should not import it.

- `training/` trains/evaluates the measurement regressor and writes reports.
- `validation/` runs measurement validation, reachability assays, and mesh-loop audits.
- `tools/` contains maintenance commands like proto generation and model downloads.

## Rule Of Thumb

If changing it can alter a Studio generation request, it belongs under `runtime/`.
If it is a CLI, report, assay, training job, or maintenance helper, it belongs under `non_runtime/`.
