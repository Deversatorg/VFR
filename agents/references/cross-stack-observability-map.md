# Cross-Stack Observability Map

Current repo snapshot for logging and telemetry.

## VFR.Auth

- Uses Serilog in `src/VFR.Auth/ApplicationAuth/Program.cs`
- Writes structured JSON logs to console
- Enables request logging through `UseSerilogRequestLogging()`
- Has domain logs in auth, SMTP, password recovery, and Stripe webhook flows
- Carries legacy logging artifacts such as `NLog.config` and `StartApp/FileLogger*` that are not part of the active path

Current gaps:

- some dev-only logs include sensitive content such as mock email bodies or reset codes
- legacy logging files can confuse future maintainers about the real sink

## VFR.ProfileApi

- Uses `AddServiceDefaults()` in `src/VFR.ProfileApi/Program.cs`
- Service defaults add OpenTelemetry logging, tracing, metrics, and optional OTLP export
- Has much stronger infrastructure observability than domain-level logging

Current gaps:

- almost no domain logs around profile fetch, draft persistence, or measurement updates
- OTLP export is config-gated, so observability quality depends heavily on deployment wiring

## VFR.AiEngine

- `main.py` configures Python logging at INFO level
- `ml_pipeline.py`, `garment_pipeline.py`, and `s3_client.py` use named loggers
- `worker.py` still uses `print()` in active task paths
- Celery status metadata exists, but that is not a replacement for logs

Current gaps:

- mixed logging style between API process and worker process
- no single structured logging format across HTTP, worker, and ML pipeline stages
- some errors are logged without consistent stack-trace handling

## VFR.AppHost

- Primarily orchestrates child services
- Has minimal direct logging of its own
- Uses `Console.WriteLine` for at least one startup message

Current gaps:

- not a central logging layer by itself
- easy to overestimate its observability role because Aspire shows child service output

## vfr-web

- Uses browser console statements in active flows
- Uses `toast` for user feedback, not durable telemetry

Current gaps:

- no centralized browser telemetry sink
- frontend-only failures can disappear once the session is gone
- console noise can linger in production unless deliberately cleaned up

## Tests

- `tests/VFR.ProfileApi.IntegrationTests/ProfileApiWebApplicationFactory.cs`
- `tests/VFR.ApiFlowTests/ProfileApiJwtFlowFactory.cs`

Both clear logging providers during test host setup. That keeps test output quiet, but it also means test runtime visibility differs from production-like startup behavior.
