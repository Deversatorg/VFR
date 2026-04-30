import contextlib
import contextvars
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone


REQUEST_ID = contextvars.ContextVar("request_id", default=None)
TRACE_ID = contextvars.ContextVar("trace_id", default=None)
TASK_ID = contextvars.ContextVar("task_id", default=None)
USER_ID = contextvars.ContextVar("user_id", default=None)

_STANDARD_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "request_id",
    "trace_id",
    "task_id",
    "user_id",
}


def generate_request_id() -> str:
    return uuid.uuid4().hex


def set_request_context(request_id: str | None = None, trace_id: str | None = None) -> None:
    REQUEST_ID.set(request_id)
    TRACE_ID.set(trace_id)


def clear_request_context() -> None:
    REQUEST_ID.set(None)
    TRACE_ID.set(None)


def set_task_context(task_id: str | None = None, user_id: str | None = None) -> None:
    TASK_ID.set(task_id)
    USER_ID.set(user_id)


def clear_task_context() -> None:
    TASK_ID.set(None)
    USER_ID.set(None)


@contextlib.contextmanager
def request_context(request_id: str | None = None, trace_id: str | None = None):
    set_request_context(request_id=request_id, trace_id=trace_id)
    try:
        yield
    finally:
        clear_request_context()


@contextlib.contextmanager
def task_context(task_id: str | None = None, user_id: str | None = None):
    set_task_context(task_id=task_id, user_id=user_id)
    try:
        yield
    finally:
        clear_task_context()


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID.get()
        record.trace_id = TRACE_ID.get()
        record.task_id = TASK_ID.get()
        record.user_id = USER_ID.get()
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name
        self._service_namespace = os.getenv("OTEL_SERVICE_NAMESPACE", "virtual-fitting-room")
        self._environment = os.getenv("DEPLOYMENT_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service.name": self._service_name,
            "service.namespace": self._service_namespace,
            "deployment.environment": self._environment,
        }

        if record.request_id:
            payload["request_id"] = record.request_id
        if record.trace_id:
            payload["trace_id"] = record.trace_id
        if record.task_id:
            payload["task_id"] = record.task_id
        if record.user_id:
            payload["user_id"] = record.user_id

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key.startswith("_") or value is None:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        elif record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(service_name: str) -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter(service_name))

    root_logger.addHandler(handler)

    logging.captureWarnings(True)

    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn.error").handlers.clear()
    logging.getLogger("uvicorn.access").handlers.clear()

    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.error").propagate = True
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
