# AI Engine Trust Boundaries

Use this reference when reviewing `src/VFR.AiEngine`.

## Main Boundaries

- Browser to FastAPI endpoints
- FastAPI to Celery and Redis
- Worker to local filesystem
- Worker to S3-compatible object storage
- FastAPI static file serving back to the browser

## Repo-Specific Security Hotspots

- CORS allows localhost development origins by default and can append extra origins from env vars.
- Avatar and garment endpoints enqueue long-running tasks and then expose status polling over HTTP.
- Garment generation writes uploads to temp files and later deletes them in the worker.
- Static file mounts expose `avatars` and `models/garments` through predictable URLs.
- S3 upload code falls back to returning a local path when credentials are missing.
- Worker results can include `model_url`, measurement metadata, and in some paths `local_path`.

## Review Questions

- Can a caller cause internal file paths or temp paths to leak through API responses or logs?
- Can a config mistake turn a public URL into a local path or otherwise change who can access artifacts?
- Can task-status or failure payloads reveal more internal detail than intended?
- Do request models and worker task args stay aligned when new fields are added?
- Are generated artifacts cleaned up, exposed, and persisted consistently across success and failure paths?
