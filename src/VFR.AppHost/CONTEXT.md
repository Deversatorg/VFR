# VFR.AppHost Context

Updated: 2026-04-27

## Role

This is the local composition root for the workspace. If you want the stack the repo is built around, start here.

## What it wires

- PostgreSQL with separate `auth` and `profiles` databases
- Redis for AI queue/result state
- Python AI engine container
- Python Celery worker container
- .NET auth service
- .NET profile API
- React/Vite frontend

## Key files

- `Program.cs` is the whole story.

## Important runtime behavior

- If `Jwt:SigningKey` is missing, AppHost generates an ephemeral dev signing key and shares it with auth/profile.
- It injects bootstrap admin credentials into auth.
- It injects `VITE_AUTH_API_URL`, `VITE_PROFILE_API_URL`, and `VITE_AI_ENGINE_API_URL` into the Vite app.
- It bind-mounts `../VFR.AiEngine/vfr_ai_engine` into both AI containers for local iteration.
- It also bind-mounts `../avatars_storage` into the AI containers.
- It passes S3-compatible storage credentials through environment variables.

## Current issues

- This file carries a lot of environment wiring and local-only behavior.
- Bind mounts are great for dev, but they are not the production deployment model.
- Restarting with a new ephemeral JWT key invalidates old local tokens.
- The host composes .NET 8 auth with .NET 9 services, so version drift shows up quickly.
- If the AI containers are already running, Python code edits often still need a container restart to refresh worker state.

## Open next

- `Program.cs`
- `../VFR.AiEngine/CONTEXT.md`
- `../vfr-web/CONTEXT.md`
