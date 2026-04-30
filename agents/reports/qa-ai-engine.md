# AI Engine QA Report

## Findings

- No P0/P1 AI Engine defects found in package import, route, Celery task, Docker, status, artifact, or legacy gRPC isolation checks completed in this pass.

- P3 - Local host Python is unavailable on PATH.
  - File/route: local QA environment
  - Impact: Contributors cannot run the documented host command `python -m compileall vfr_ai_engine` directly on this machine. Docker-based AI checks work, so this is an environment gap rather than a package regression.
  - Reproduction: run `python --version` or `py --version`; both were unavailable in this QA session.

- P3 - AI unit tests assume repository-depth paths when mounted into Docker.
  - File/line: `src/VFR.AiEngine/tests/test_status_endpoints.py:159`
  - Impact: Mounting only `src/VFR.AiEngine` at `/work` caused import-time errors because some tests use `Path(__file__).resolve().parents[3]`. Mounting the full repo at `/repo` made the same suite pass. This can confuse containerized local QA.
  - Reproduction: run AI unittest discovery with only the AI Engine folder mounted into the container; then rerun with the full repo mounted.

## Scope

- Checked `src/VFR.AiEngine` package split, deleted root entrypoint assumptions, Dockerfile build, FastAPI routes, Celery task names, artifact URL contracts, profile result metadata, gRPC legacy isolation, and lightweight test imports.

## Commands Run

- `docker build -t vfr-aiengine-qa .`
  - Cwd: `C:\projects\virtual-fitting-room\src\VFR.AiEngine`
  - Result: PASS.
- `docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v C:\projects\virtual-fitting-room\src\VFR.AiEngine:/work -w /work vfr-aiengine-qa python -m compileall vfr_ai_engine`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS.
- `docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v C:\projects\virtual-fitting-room\src\VFR.AiEngine:/work -w /work vfr-aiengine-qa python -m unittest discover -s tests -v`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: FAIL due test path assumption under shallow mount.
- `docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v C:\projects\virtual-fitting-room:/repo -w /repo/src/VFR.AiEngine vfr-aiengine-qa python -m unittest discover -s tests -v`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, 17/17 tests.
- `docker run --rm vfr-aiengine-qa python -m vfr_ai_engine.tools.generate_protos`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS.
- `curl http://127.0.0.1:55077/health`
  - Cwd: `C:\projects\virtual-fitting-room`
  - Result: PASS, returned `{"status":"healthy"}` from AppHost runtime.

## E2E Scenarios

- AI HTTP health under AppHost
  - Input state: AppHost stack running.
  - Expected: AI Engine responds to `/health`.
  - Actual: PASS.

- AI HTTP route contract
  - Input state: Static route check.
  - Expected: `POST /api/v1/avatar/generate`, `POST /api/v1/avatar/generate-from-profile`, `GET /api/v1/avatar/status/{task_id}`, `POST /api/v1/garment/generate`, and `GET /api/v1/garment/status/{task_id}` remain present.
  - Actual: PASS in `src/VFR.AiEngine/vfr_ai_engine/api/routes.py:33`, `:52`, `:88`, `:122`, and `:141`.

- Celery task names
  - Input state: Static task check.
  - Expected: `generate_3d_avatar`, `generate_3d_avatar_from_profile`, and `generate_garment_3d` remain unchanged.
  - Actual: PASS in `src/VFR.AiEngine/vfr_ai_engine/tasks/avatar.py:14`, `:36`, and `src/VFR.AiEngine/vfr_ai_engine/tasks/garments.py:17`.

- Artifact URL contract
  - Input state: AI unit tests and static status check.
  - Expected: Avatar local fallback accepts `/models/...`; garment output uses `/models/garments/...`.
  - Actual: PASS by AI tests and static checks; S3 fallback test logged `/models/profile_demo.glb`.

- Profile avatar result metadata
  - Input state: Static pipeline/task/status check.
  - Expected: Profile-generated avatar success includes `model_url`, `measurements`, `targets`, `measurement_sources`.
  - Actual: PASS in `src/VFR.AiEngine/vfr_ai_engine/avatar/pipeline.py:799` and `src/VFR.AiEngine/vfr_ai_engine/tasks/avatar.py:99`.

- gRPC legacy surface
  - Input state: Static search and AppHost runtime.
  - Expected: gRPC server may start for legacy compatibility, but ProfileApi active path remains HTTP.
  - Actual: PASS. Static search found gRPC only in AI Engine server/test stubs, not a ProfileApi/.NET consumer.

## Residual Test Gaps

- Full SMPL-X/ML generation was not run because it is too heavy for this local QA pass and may need model assets/GPU setup.
- Real S3 upload was not exercised; fallback/local artifact behavior was tested.
- Authenticated ProfileApi-to-AI generation E2E was blocked by Auth runtime account failures.
- Browser-fetch validation of a newly generated `/models/...` artifact was not completed because no successful generation job was queued through the authenticated app path.

## Assumptions

- Docker is the supported fallback when host Python is unavailable.
- Generated proto helper now targets the AI Engine proto and was smoke-tested in the image.
- Running gRPC on AI startup is legacy-compatible behavior, not evidence that ProfileApi uses it.
