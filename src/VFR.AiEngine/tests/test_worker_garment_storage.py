from __future__ import annotations

import importlib
import os
import shutil
import sys
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
AI_ENGINE_DIR = REPO_ROOT / "src" / "VFR.AiEngine"
TEST_TEMP_ROOT = REPO_ROOT / "tmp" / "aiengine-tests"


class FakeCeleryConf:
    def update(self, **kwargs):
        self.values = kwargs


class FakeCelery:
    def __init__(self, *args, **kwargs):
        self.conf = FakeCeleryConf()

    def task(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class FakeTask:
    def __init__(self):
        self.states: list[dict[str, object]] = []

    def update_state(self, state=None, meta=None):
        self.states.append({"state": state, "meta": meta})


def _install_fake_modules(output_glb_path: Path) -> dict[str, object]:
    originals: dict[str, object] = {}

    def register(name: str, module: types.ModuleType) -> None:
        if name not in originals and name in sys.modules:
            originals[name] = sys.modules[name]
        sys.modules[name] = module

    tasks_app = types.ModuleType("vfr_ai_engine.tasks.app")
    tasks_app.celery_app = FakeCelery()
    register("vfr_ai_engine.tasks.app", tasks_app)

    class FakeGarmentMLPipeline:
        def apply_texture_to_primitive(self, primitive_type, image_bytes):
            output_glb_path.write_bytes(b"glb")
            return str(output_glb_path)

    garment_pipeline = types.ModuleType("vfr_ai_engine.garments.pipeline")
    garment_pipeline.GarmentMLPipeline = FakeGarmentMLPipeline
    register("vfr_ai_engine.garments.pipeline", garment_pipeline)

    return originals


def _restore_modules(originals: dict[str, object]) -> None:
    for name in ["vfr_ai_engine.garments.pipeline", "vfr_ai_engine.tasks.app", "vfr_ai_engine.tasks.garments", "vfr_ai_engine.paths"]:
        original = originals.get(name)
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def _load_worker_module() -> types.ModuleType:
    sys.path.insert(0, str(AI_ENGINE_DIR))
    sys.modules.pop("vfr_ai_engine.tasks.garments", None)
    sys.modules.pop("vfr_ai_engine.paths", None)
    return importlib.import_module("vfr_ai_engine.tasks.garments")


class AiEngineWorkerGarmentStorageTests(unittest.TestCase):
    def setUp(self):
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.tempdir = TEST_TEMP_ROOT / f"worker-{uuid.uuid4().hex}"
        self.tempdir.mkdir()
        self.garment_dir = self.tempdir / "shared-garments"
        self.output_glb_path = self.tempdir / "pipeline-output.glb"
        self.fake_modules = _install_fake_modules(self.output_glb_path)

    def tearDown(self):
        _restore_modules(self.fake_modules)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_garment_task_moves_artifact_to_shared_served_dir(self):
        input_image = self.tempdir / "upload.png"
        input_image.write_bytes(b"image")

        with patch.dict(os.environ, {"GARMENT_STORAGE_DIR": str(self.garment_dir), "REDIS_URL": "redis://test/0"}):
            worker = _load_worker_module()

        task = FakeTask()
        result = worker.generate_garment_3d(task, "task-123", "tshirt", str(input_image))

        expected_path = self.garment_dir / "garment_task-123.glb"
        self.assertEqual(result["model_url"], "/models/garments/garment_task-123.glb")
        self.assertEqual(Path(result["local_path"]), expected_path)
        self.assertTrue(expected_path.exists())
        self.assertFalse(input_image.exists())


if __name__ == "__main__":
    unittest.main()
