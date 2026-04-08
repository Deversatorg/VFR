# Logging Standard

This repository uses one observability contract across all active slices.

## Target Stack

- OpenTelemetry for shared observability semantics
- OTLP as the transport when an exporter is configured
- structured JSON logs for local and container stdout
- platform-native logger APIs in code:
  - `ILogger<T>` in .NET
  - `logging.getLogger(...)` in Python
  - a shared browser logger wrapper in frontend code

## Required Fields

Every runtime log should carry these fields when available:

- `service.name`
- `service.namespace`
- `deployment.environment`
- `request_id`
- `trace_id`
- `span_id`
- `task_id`

Domain-specific fields are encouraged when they are safe:

- `user_id`
- `profile_id`
- `draft_id`
- `subscription_id`
- `plan_id`

Never log passwords, reset codes, JWTs, refresh tokens, webhook bodies, or secrets.

## Levels

- `Information`: meaningful state transitions and request completions
- `Warning`: expected but undesirable fallback, validation, or recoverable failure
- `Error`: failed operation or unhandled exception
- `Debug` and `Trace`: local diagnosis only, never relied on for production behavior

## Service Rules

### .NET services

- Use `AddServiceDefaults()` for logging and OpenTelemetry wiring
- Use `UseDefaultRequestLogging()` for request completion logs
- Use message templates instead of string interpolation in hot paths
- Keep appsettings log levels aligned across services unless there is a clear reason to diverge

### Python services

- Use `logging.getLogger(...)`, not `print()`, in runtime code
- Emit JSON logs to stdout
- Propagate `X-Request-ID` and task correlation through middleware and worker context
- Log task start, task completion, and task failure once each

### Frontend

- Use the shared browser logger wrapper instead of direct `console.*`
- Treat toasts as UX only, not durable telemetry
- Log only warnings and errors in production-facing flows unless a debug session explicitly needs more

## Rollout Intent

The repo currently aims for contract consistency first:

1. common fields
2. consistent sinks and stdout format
3. safe content
4. OTLP export where configured

Backend storage and dashboards may evolve independently as long as this contract stays stable.
