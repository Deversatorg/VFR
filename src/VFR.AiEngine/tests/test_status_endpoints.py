from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
AI_ENGINE_DIR = REPO_ROOT / "src" / "VFR.AiEngine"
MAIN_PATH = AI_ENGINE_DIR / "main.py"


class FakeAsyncResult:
    registry: dict[str, dict[str, object]] = {}

    def __init__(self, task_id: str, app=None):
        try:
            payload = self.registry[task_id]
        except KeyError as exc:
            raise AssertionError(f"Missing fake AsyncResult payload for {task_id}") from exc

        self.task_id = task_id
        self.app = app
        self.state = payload["state"]
        self.info = payload.get("info")
        self.result = payload.get("result")


class FakeQueuedTask:
    def __init__(self, task_id: str):
        self.id = task_id


class FakeCeleryTask:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def apply_async(self, args=None, task_id=None, **kwargs):
        self.calls.append(
            {
                "args": list(args or []),
                "task_id": task_id,
                "kwargs": kwargs,
            }
        )
        return FakeQueuedTask(task_id or "generated-task-id")


def _install_fake_modules() -> dict[str, object]:
    originals: dict[str, object] = {}

    def register(name: str, module: types.ModuleType) -> None:
        if name not in originals and name in sys.modules:
            originals[name] = sys.modules[name]
        sys.modules[name] = module

    avatar_pb2 = types.ModuleType("avatar_pb2")
    avatar_pb2.AvatarRequest = type("AvatarRequest", (), {})
    avatar_pb2.AvatarResponse = type("AvatarResponse", (), {})
    register("avatar_pb2", avatar_pb2)

    avatar_pb2_grpc = types.ModuleType("avatar_pb2_grpc")
    avatar_pb2_grpc.AvatarServiceServicer = type("AvatarServiceServicer", (), {})
    avatar_pb2_grpc.add_AvatarServiceServicer_to_server = lambda *args, **kwargs: None
    register("avatar_pb2_grpc", avatar_pb2_grpc)

    worker = types.ModuleType("worker")
    worker.celery_app = object()
    worker.generate_3d_avatar = FakeCeleryTask()
    worker.generate_3d_avatar_from_profile = FakeCeleryTask()
    worker.generate_garment_3d = FakeCeleryTask()
    register("worker", worker)

    celery = types.ModuleType("celery")
    celery.__path__ = []
    register("celery", celery)

    celery_result = types.ModuleType("celery.result")
    celery_result.AsyncResult = FakeAsyncResult
    register("celery.result", celery_result)

    grpc = types.ModuleType("grpc")
    grpc.ServicerContext = type("ServicerContext", (), {})
    grpc.server = lambda *args, **kwargs: None
    register("grpc", grpc)

    uvicorn = types.ModuleType("uvicorn")
    uvicorn.run = lambda *args, **kwargs: None
    register("uvicorn", uvicorn)

    return originals


def _restore_modules(originals: dict[str, object]) -> None:
    for name in ["avatar_pb2", "avatar_pb2_grpc", "worker", "celery.result", "celery", "grpc", "uvicorn"]:
        original = originals.get(name)
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def _load_main_module() -> types.ModuleType:
    module_name = "vfr_aiengine_main_contract"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(module_name, MAIN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MAIN_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class AiEngineStatusEndpointContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tempdir = tempfile.TemporaryDirectory(prefix="vfr-ai-engine-tests-")
        cls._original_cwd = os.getcwd()
        cls._original_dirname = os.path.dirname
        cls._fake_app_base = Path(cls._tempdir.name) / "shadow-ai-engine"
        cls._fake_app_base.mkdir(parents=True, exist_ok=True)

        def fake_dirname(path: str) -> str:
            if Path(path).resolve() == MAIN_PATH.resolve():
                return str(cls._fake_app_base)
            return cls._original_dirname(path)

        cls._fake_modules = _install_fake_modules()
        try:
            os.chdir(cls._tempdir.name)
            with patch("os.path.dirname", side_effect=fake_dirname):
                cls.main = _load_main_module()
        finally:
            os.chdir(cls._original_cwd)

        registered_paths = {route.path for route in cls.main.app.router.routes}
        if "/api/v1/avatar/status/{task_id}" not in registered_paths:
            raise AssertionError("avatar status route is not registered")
        if "/api/v1/garment/status/{task_id}" not in registered_paths:
            raise AssertionError("garment status route is not registered")
        if "/api/v1/avatar/generate-from-profile" not in registered_paths:
            raise AssertionError("avatar generate-from-profile route is not registered")

        FakeAsyncResult.registry.clear()

    def setUp(self):
        FakeAsyncResult.registry.clear()

    @classmethod
    def tearDownClass(cls):
        _restore_modules(cls._fake_modules)
        cls._tempdir.cleanup()

    def _assert_status_payload(self, payload, task_id, state, progress, message, result=None):
        self.assertEqual(payload["task_id"], task_id)
        self.assertEqual(payload["status"], state)
        self.assertEqual(payload["progress"], progress)
        self.assertEqual(payload["message"], message)

        if result is None:
            self.assertNotIn("result", payload)
        else:
            self.assertEqual(payload["result"], result)

    def _exercise_status_endpoint(self, path_template: str):
        cases = [
            (
                "pending",
                {"state": "PENDING"},
                {"progress": 0, "message": "Task is waiting for a worker..."},
            ),
            (
                "progress",
                {"state": "PROGRESS", "info": {"progress": 42, "message": "Halfway there"}},
                {"progress": 42, "message": "Halfway there"},
            ),
            (
                "success",
                {"state": "SUCCESS", "result": {"model_url": "/models/demo.glb"}},
                {"progress": 100, "message": "Completed", "result": {"model_url": "/models/demo.glb"}},
            ),
            (
                "failure",
                {"state": "FAILURE", "result": RuntimeError("generation failed")},
                {"progress": 0, "message": "generation failed"},
            ),
        ]

        for suffix, fake_result, expected in cases:
            with self.subTest(state=fake_result["state"]):
                task_id = f"{path_template.split('/')[3]}-{suffix}"
                FakeAsyncResult.registry[task_id] = fake_result

                handler = (
                    self.main.get_avatar_status
                    if "avatar" in path_template
                    else self.main.get_garment_status
                )
                payload = asyncio.run(handler(task_id))
                self._assert_status_payload(
                    payload,
                    task_id,
                    fake_result["state"],
                    expected["progress"],
                    expected["message"],
                    expected.get("result"),
                )

    def test_avatar_status_contract(self):
        self._exercise_status_endpoint("/api/v1/avatar/status/{task_id}")

    def test_garment_status_contract(self):
        self._exercise_status_endpoint("/api/v1/garment/status/{task_id}")

    def test_generate_from_profile_enqueues_expected_payload(self):
        request = self.main.ProfileAvatarRequest(
            user_id="flow-user",
            height=181.0,
            weight=77.0,
            body_type="athletic",
            gender="male",
            muscularity=72.0,
            body_fat_percentage=14.0,
            chest=101.0,
            waist=83.0,
            hip=98.0,
            shoulder=46.0,
            calf=38.0,
            arm_length=62.0,
            torso_length=64.0,
            leg_length=108.0,
            face_image_url="",
        )

        response = asyncio.run(self.main.generate_avatar_from_profile(request))

        self.assertEqual(response.status, "accepted")
        self.assertEqual(response.message, "Parametric avatar generation task queued.")
        self.assertTrue(response.task_id)

        worker_module = sys.modules["worker"]
        self.assertEqual(len(worker_module.generate_3d_avatar_from_profile.calls), 1)

        recorded_call = worker_module.generate_3d_avatar_from_profile.calls[0]
        self.assertEqual(recorded_call["task_id"], response.task_id)
        self.assertEqual(
            recorded_call["args"],
            [
                response.task_id,
                "flow-user",
                181.0,
                77.0,
                "athletic",
                "male",
                72.0,
                14.0,
                101.0,
                83.0,
                98.0,
                46.0,
                38.0,
                62.0,
                64.0,
                108.0,
                "",
            ],
        )


if __name__ == "__main__":
    unittest.main()
