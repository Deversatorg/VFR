from __future__ import annotations

import asyncio
import importlib
import os
import shutil
import sys
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

CURRENT_FILE = Path(__file__).resolve()
if str(CURRENT_FILE).startswith("/app/"):
    AI_ENGINE_DIR = Path("/app")
    TEST_TEMP_ROOT = Path("/workspace-tmp") / "aiengine-tests"
else:
    REPO_ROOT = CURRENT_FILE.parents[3]
    AI_ENGINE_DIR = REPO_ROOT / "src" / "VFR.AiEngine"
    TEST_TEMP_ROOT = REPO_ROOT / "tmp" / "aiengine-tests"
MAIN_MODULE = "vfr_ai_engine.runtime.api.main"


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

    class FakeRoute:
        def __init__(self, path: str):
            self.path = path

    class FakeFastAPI:
        def __init__(self, *args, **kwargs):
            self.router = types.SimpleNamespace(routes=[])
            self.mounts = []

        def _route_decorator(self, path: str):
            self.router.routes.append(FakeRoute(path))

            def decorator(func):
                return func

            return decorator

        def get(self, path: str, **kwargs):
            return self._route_decorator(path)

        def post(self, path: str, **kwargs):
            return self._route_decorator(path)

        def middleware(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def mount(self, *args, **kwargs):
            self.mounts.append((args, kwargs))
            return None

        def add_middleware(self, *args, **kwargs):
            return None

        def include_router(self, router):
            self.router.routes.extend(router.routes)
            return None

    class FakeAPIRouter:
        def __init__(self, *args, **kwargs):
            self.routes = []

        def _route_decorator(self, path: str):
            self.routes.append(FakeRoute(path))

            def decorator(func):
                return func

            return decorator

        def get(self, path: str, **kwargs):
            return self._route_decorator(path)

        def post(self, path: str, **kwargs):
            return self._route_decorator(path)

    class FakeHTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class FakeBaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    fastapi = types.ModuleType("fastapi")
    fastapi.APIRouter = FakeAPIRouter
    fastapi.FastAPI = FakeFastAPI
    fastapi.HTTPException = FakeHTTPException
    fastapi.UploadFile = type("UploadFile", (), {})
    fastapi.File = lambda default=None, **kwargs: default
    fastapi.Form = lambda default=None, **kwargs: default
    fastapi.Request = type("Request", (), {})
    register("fastapi", fastapi)

    fastapi_middleware = types.ModuleType("fastapi.middleware")
    fastapi_middleware.__path__ = []
    register("fastapi.middleware", fastapi_middleware)

    fastapi_cors = types.ModuleType("fastapi.middleware.cors")
    fastapi_cors.CORSMiddleware = type("CORSMiddleware", (), {})
    register("fastapi.middleware.cors", fastapi_cors)

    fastapi_staticfiles = types.ModuleType("fastapi.staticfiles")
    fastapi_staticfiles.StaticFiles = lambda *args, **kwargs: object()
    register("fastapi.staticfiles", fastapi_staticfiles)

    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = FakeBaseModel
    register("pydantic", pydantic)

    avatar_pb2 = types.ModuleType("avatar_pb2")
    avatar_pb2.AvatarRequest = type("AvatarRequest", (), {})
    avatar_pb2.AvatarResponse = type("AvatarResponse", (), {})
    register("avatar_pb2", avatar_pb2)

    avatar_pb2_grpc = types.ModuleType("avatar_pb2_grpc")
    avatar_pb2_grpc.AvatarServiceServicer = type("AvatarServiceServicer", (), {})
    avatar_pb2_grpc.add_AvatarServiceServicer_to_server = lambda *args, **kwargs: None
    register("avatar_pb2_grpc", avatar_pb2_grpc)

    tasks_app = types.ModuleType("vfr_ai_engine.runtime.tasks.app")
    tasks_app.celery_app = object()
    register("vfr_ai_engine.runtime.tasks.app", tasks_app)

    avatar_tasks = types.ModuleType("vfr_ai_engine.runtime.tasks.avatar")
    avatar_tasks.generate_3d_avatar = FakeCeleryTask()
    avatar_tasks.generate_3d_avatar_from_profile = FakeCeleryTask()
    register("vfr_ai_engine.runtime.tasks.avatar", avatar_tasks)

    garment_tasks = types.ModuleType("vfr_ai_engine.runtime.tasks.garments")
    garment_tasks.generate_garment_3d = FakeCeleryTask()
    register("vfr_ai_engine.runtime.tasks.garments", garment_tasks)

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
    for name in [
        "fastapi.staticfiles",
        "fastapi.middleware.cors",
        "fastapi.middleware",
        "fastapi",
        "pydantic",
        "avatar_pb2",
        "avatar_pb2_grpc",
        "vfr_ai_engine.runtime.tasks.app",
        "vfr_ai_engine.runtime.tasks.avatar",
        "vfr_ai_engine.runtime.tasks.garments",
        "celery.result",
        "celery",
        "grpc",
        "uvicorn",
    ]:
        original = originals.get(name)
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def _load_main_module() -> types.ModuleType:
    for module_name in [
        "vfr_ai_engine.runtime.api.main",
        "vfr_ai_engine.runtime.api.app",
        "vfr_ai_engine.runtime.api.routes",
        "vfr_ai_engine.runtime.api.static_files",
        "vfr_ai_engine.runtime.paths",
    ]:
        sys.modules.pop(module_name, None)

    sys.path.insert(0, str(AI_ENGINE_DIR))
    return importlib.import_module(MAIN_MODULE)


class AiEngineStatusEndpointContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        cls._tempdir = TEST_TEMP_ROOT / f"status-{uuid.uuid4().hex}"
        cls._tempdir.mkdir()
        cls._original_cwd = os.getcwd()
        cls._garment_dir = cls._tempdir / "shared-garments"

        cls._fake_modules = _install_fake_modules()
        try:
            os.chdir(cls._tempdir)
            with patch.dict(os.environ, {"GARMENT_STORAGE_DIR": str(cls._garment_dir)}):
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
        if cls.main._GARMENTS_DIR != str(cls._garment_dir):
            raise AssertionError("garment storage dir did not honor GARMENT_STORAGE_DIR")

        FakeAsyncResult.registry.clear()

    def setUp(self):
        FakeAsyncResult.registry.clear()

    @classmethod
    def tearDownClass(cls):
        _restore_modules(cls._fake_modules)
        shutil.rmtree(cls._tempdir, ignore_errors=True)

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
                {
                    "state": "SUCCESS",
                    "result": {
                        "model_url": "/models/demo.glb",
                        "measurements": {"chest_cm": 101.0},
                        "targets": {"chest_cm": 100.0},
                        "measurement_sources": {"chest_cm": "user"},
                    },
                },
                {
                    "progress": 100,
                    "message": "Completed",
                    "result": {
                        "model_url": "/models/demo.glb",
                        "measurements": {"chest_cm": 101.0},
                        "targets": {"chest_cm": 100.0},
                        "measurement_sources": {"chest_cm": "user"},
                    },
                },
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

    def test_avatar_success_without_fetchable_model_url_becomes_failure(self):
        task_id = "avatar-invalid-success"
        FakeAsyncResult.registry[task_id] = {
            "state": "SUCCESS",
            "result": {"model_url": "/tmp/profile_demo.glb"},
        }

        payload = asyncio.run(self.main.get_avatar_status(task_id))

        self.assertEqual(payload["task_id"], task_id)
        self.assertEqual(payload["status"], "FAILURE")
        self.assertEqual(payload["progress"], 0)
        self.assertEqual(payload["message"], "Worker completed without a fetchable model_url.")

    def test_avatar_failure_uses_worker_error_metadata(self):
        task_id = "avatar-smplx-unavailable"
        FakeAsyncResult.registry[task_id] = {
            "state": "FAILURE",
            "info": {"error": "SMPL-X unavailable for gender='male' and neutral fallback also failed."},
            "result": RuntimeError("generic celery wrapper"),
        }

        payload = asyncio.run(self.main.get_avatar_status(task_id))

        self.assertEqual(payload["task_id"], task_id)
        self.assertEqual(payload["status"], "FAILURE")
        self.assertEqual(payload["message"], "SMPL-X unavailable for gender='male' and neutral fallback also failed.")

    def test_garment_status_contract(self):
        self._exercise_status_endpoint("/api/v1/garment/status/{task_id}")

    def test_fastapi_serves_garments_from_shared_storage_dir(self):
        mounted_paths = [args[0] for args, _ in self.main.app.mounts]

        self.assertIn("/models/garments", mounted_paths)
        self.assertTrue(self._garment_dir.exists())

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

        avatar_tasks = sys.modules["vfr_ai_engine.runtime.tasks.avatar"]
        self.assertEqual(len(avatar_tasks.generate_3d_avatar_from_profile.calls), 1)

        recorded_call = avatar_tasks.generate_3d_avatar_from_profile.calls[0]
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
