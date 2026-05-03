"""Celery application configuration shared by all AI engine tasks."""

from __future__ import annotations

import os

from celery import Celery

from vfr_ai_engine.runtime.observability.logging import configure_logging

configure_logging("vfr-aiengine-worker")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0").replace("tcp://", "redis://")

celery_app = Celery("avatar_tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)

# Import task modules so Celery registers them when loading this app.
from vfr_ai_engine.runtime.tasks import avatar as _avatar_tasks  # noqa: E402,F401
from vfr_ai_engine.runtime.tasks import garments as _garment_tasks  # noqa: E402,F401

