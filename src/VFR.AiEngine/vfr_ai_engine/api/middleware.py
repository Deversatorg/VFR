"""HTTP middleware for request IDs, trace correlation, and structured request logs."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request

from vfr_ai_engine.observability.logging import generate_request_id, request_context


def extract_trace_id(request: Request) -> str | None:
    traceparent = request.headers.get("traceparent", "").strip()
    if traceparent:
        parts = traceparent.split("-")
        if len(parts) >= 4 and len(parts[1]) == 32:
            return parts[1]

    return None


def install_request_logging(app: FastAPI, logger: logging.Logger) -> None:
    @app.middleware("http")
    async def add_request_logging(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "").strip() or generate_request_id()
        trace_id = extract_trace_id(request) or request_id
        started_at = time.perf_counter()

        with request_context(request_id=request_id, trace_id=trace_id):
            try:
                response = await call_next(request)
            except Exception:
                elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.exception(
                    "HTTP request failed.",
                    extra={
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "elapsed_ms": elapsed_ms,
                    },
                )
                raise

            response.headers["X-Request-ID"] = request_id

            if request.url.path not in {"/", "/health"}:
                elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
                log_fn = logger.warning if response.status_code >= 400 else logger.info
                log_fn(
                    "HTTP request completed.",
                    extra={
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "status_code": response.status_code,
                        "elapsed_ms": elapsed_ms,
                    },
                )

            return response

