"""Normalization for Celery task status payloads returned by HTTP polling."""

from __future__ import annotations

from typing import Any


def is_fetchable_model_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    model_url = value.strip()
    return (
        model_url.startswith("http://")
        or model_url.startswith("https://")
        or model_url.startswith("/models/")
    )


def failure_message(info: Any, result: Any) -> str:
    if isinstance(info, dict):
        for key in ("error", "message"):
            value = info.get(key)
            if value:
                return str(value)

    return str(result) if result else "Generation failed."


def task_status_response(task_id: str, state: str, info: Any = None, result: Any = None) -> dict[str, Any]:
    response: dict[str, Any] = {
        "task_id": task_id,
        "status": state,
        "progress": 0,
        "message": "",
    }

    if state == "PENDING":
        response["message"] = "Task is waiting for a worker..."
    elif state == "STARTED":
        response["progress"] = 5
        response["message"] = "Task started."
    elif state == "PROGRESS":
        if isinstance(info, dict):
            response["progress"] = info.get("progress", 0)
            response["message"] = info.get("message", "")
    elif state == "SUCCESS":
        if not isinstance(result, dict):
            response["status"] = "FAILURE"
            response["message"] = "Worker completed without a result payload."
            return response

        if not is_fetchable_model_url(result.get("model_url")):
            response["status"] = "FAILURE"
            response["message"] = "Worker completed without a fetchable model_url."
            return response

        response["progress"] = 100
        response["message"] = "Completed"
        response["result"] = result
    elif state == "FAILURE":
        response["message"] = failure_message(info, result)

    return response

