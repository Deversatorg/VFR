# Logging Checklist

Use this checklist when auditing observability across the repo.

## Per-Service Questions

For each service, answer:

- Which logger or provider is configured?
- Where do logs actually go?
- Are request logs emitted automatically?
- Are domain events logged at all?
- Are errors logged once, or duplicated at several layers?
- Are there trace or correlation identifiers in practice?
- Do tests alter logging providers and hide runtime behavior?

## Signal Types

Classify findings into these buckets:

- Coverage gap: important state changes happen with no domain log
- Sink gap: logs exist but only in browser console, local files, or conditional exporters
- Structure gap: plain text, inconsistent templates, no correlation identifiers
- Safety gap: sensitive values or secrets appear in logs
- Noise gap: hot-path spam, duplicate framework logs, or logs that bury the useful signal

## .NET Review Points

- `Program.cs` and `appsettings*.json`
- `builder.Logging`, `AddSerilog`, `AddOpenTelemetry`, `UseSerilogRequestLogging`
- health checks, exception handlers, and middleware-level request logging
- whether OTLP export is always on, environment-gated, or config-gated
- whether business handlers log the state transitions that matter

## Python Review Points

- `logging.basicConfig`, named loggers, uvicorn defaults, Celery worker output
- `print()` calls in request paths, worker tasks, and cleanup flows
- exception logging that drops stack traces or duplicates failures
- long-running ML steps that need start, finish, and failure markers
- artifact upload and fallback behavior that only surface in logs

## Frontend Review Points

- `console.error`, `console.warn`, and `console.log` usage in active flows
- whether user-visible toasts are backed by any durable telemetry
- whether network failures can be diagnosed after the browser session is gone
- whether noisy dev-only logs leak into production builds

## Operational Questions

- Can an operator trace one auth or billing request end to end?
- Can an operator trace one avatar generation from HTTP request to Celery result to artifact upload?
- Can an operator distinguish expected mock or local fallback behavior from production misconfiguration?
- If OTLP is off, do we still have usable logs in container stdout?

## Recommended Output Shape

Summarize by slice:

- Current state
- Main gaps
- Immediate risks
- Standard to converge on
