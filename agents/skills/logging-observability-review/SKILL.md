---
name: logging-observability-review
description: Audit logging, telemetry, and sinks across .NET, Python, AppHost, and frontend. Use for log coverage, structured output, OTLP, and noise review.
---

# Logging Observability Review

Do NOT use this skill when:

- the goal is auth or AI exploit review rather than observability quality -> use `auth-security` or `ai-engine-security`
- the task is a narrow code fix with no logging or telemetry question -> use the owning domain skill
- the goal is browser-flow validation rather than runtime signal quality -> use `e2e-validation`

Read these first:

- `AGENTS.md`
- the nearest service `CONTEXT.md`
- `agents/references/cross-stack-observability-map.md`
- `agents/references/logging-checklist.md`

## Entry Points

- `src/VFR.Auth/ApplicationAuth/Program.cs`
- `src/VFR.Auth/ApplicationAuth/appsettings.json`
- `src/VFR.Auth/ApplicationAuth/appsettings.Development.json`
- `src/VFR.Auth/ApplicationAuth/Features`
- `src/VFR.ServiceDefaults/Extensions.cs`
- `src/VFR.ProfileApi/Program.cs`
- `src/VFR.AppHost/Program.cs`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/api/main.py`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/tasks`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/avatar/pipeline.py`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/garments/pipeline.py`
- `src/VFR.AiEngine/vfr_ai_engine/runtime/storage/s3_client.py`
- `src/vfr-web/src`
- test host factories under `tests/VFR.ProfileApi.IntegrationTests` and `tests/VFR.ApiFlowTests`

## Review Goals

### Coverage

- identify which services emit logs, traces, or metrics and which only write to stdout or browser console
- identify where request logging, startup logging, worker-task logging, and error logging are present or missing
- separate framework logs from domain logs so sparse business visibility is visible

### Structure

- check whether logs are structured or plain text
- check whether request IDs, trace IDs, task IDs, and service context can be correlated across services
- prefer message templates over string interpolation in hot paths

### Export Path

- find the real sink: console, OTLP exporter, file sink, browser console, or nowhere useful
- verify whether OpenTelemetry exporters are conditional on config and whether that leaves silent gaps
- treat container stdout as the default source of truth unless a real collector path is wired

### Signal Quality

- flag noisy info/debug logs in hot paths
- flag missing business-state logs around auth, billing, draft persistence, avatar generation, and artifact upload
- flag tests that clear providers or otherwise hide real runtime behavior

### Safety

- look for reset codes, email bodies, secrets, tokens, local paths, or third-party payload details leaking into logs
- look for mock-mode or localhost fallbacks that only appear in logs and can be missed operationally

## Repo-Specific Heuristics

- `VFR.Auth` is the most mature logging slice today: treat Serilog JSON console output and request logging as the baseline to compare against
- `VFR.ProfileApi` has service-default observability infrastructure, but may still lack domain-level log statements
- `VFR.AiEngine` currently mixes Python `logging` and `print`; prefer one logging path for worker and API code
- `vfr-web` browser logs are developer-visible only until a real frontend telemetry sink exists
- `VFR.AppHost` mostly orchestrates child processes; do not over-credit it for service observability

When reporting findings, separate:

1. missing coverage
2. format or correlation mismatch
3. sensitive-data leakage
4. export or retention gap
5. noise or performance issue
