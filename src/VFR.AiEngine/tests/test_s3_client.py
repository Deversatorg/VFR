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


def _install_fake_modules() -> dict[str, object]:
    originals: dict[str, object] = {}

    def register(name: str, module: types.ModuleType) -> None:
        if name not in originals and name in sys.modules:
            originals[name] = sys.modules[name]
        sys.modules[name] = module

    boto3 = types.ModuleType("boto3")
    boto3.client = lambda *args, **kwargs: object()
    register("boto3", boto3)

    botocore = types.ModuleType("botocore")
    botocore.__path__ = []
    register("botocore", botocore)

    botocore_client = types.ModuleType("botocore.client")
    botocore_client.Config = lambda *args, **kwargs: object()
    register("botocore.client", botocore_client)

    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    register("dotenv", dotenv)

    return originals


def _restore_modules(originals: dict[str, object]) -> None:
    for name in ["boto3", "botocore.client", "botocore", "dotenv"]:
        original = originals.get(name)
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def _load_s3_client_module():
    sys.path.insert(0, str(AI_ENGINE_DIR))
    for module_name in ["vfr_ai_engine.storage.s3_client", "vfr_ai_engine.paths"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("vfr_ai_engine.storage.s3_client")


class S3ClientFallbackContractTests(unittest.TestCase):
    def test_local_fallback_returns_served_models_url(self):
        fake_modules = _install_fake_modules()
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        tempdir = TEST_TEMP_ROOT / f"s3-{uuid.uuid4().hex}"
        tempdir.mkdir()
        try:
            source_path = tempdir / "profile_demo.glb"
            source_path.write_bytes(b"glb")
            avatar_dir = tempdir / "avatars"

            env = {
                "S3_ENDPOINT_URL": "",
                "S3_ACCESS_KEY": "",
                "S3_SECRET_KEY": "",
                "AVATAR_STORAGE_DIR": str(avatar_dir),
            }

            try:
                with patch.dict(os.environ, env, clear=False):
                    module = _load_s3_client_module()
                    result = module.upload_glb(str(source_path), "avatars/profile_demo.glb")
            finally:
                _restore_modules(fake_modules)

            self.assertEqual(result, "/models/profile_demo.glb")
            self.assertEqual((avatar_dir / "profile_demo.glb").read_bytes(), b"glb")
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
