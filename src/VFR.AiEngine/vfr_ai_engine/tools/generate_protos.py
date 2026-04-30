"""Regenerate root-level avatar_pb2.py and avatar_pb2_grpc.py from the AI engine proto."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

engine_root = Path(__file__).resolve().parents[2]
repo_root = engine_root.parent.parent
proto_dir = engine_root
proto_file = proto_dir / "avatar.proto"
shared_proto_file = repo_root / "protos" / "avatar.proto"

def _normalize_proto_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


if (
    shared_proto_file.exists()
    and _normalize_proto_text(shared_proto_file.read_text()) != _normalize_proto_text(proto_file.read_text())
):
    raise RuntimeError(
        "Proto drift detected: src/VFR.AiEngine/avatar.proto and protos/avatar.proto differ. "
        "Keep them in sync before regenerating Python stubs."
    )

subprocess.check_call([
    sys.executable,
    "-m",
    "grpc_tools.protoc",
    f"-I{proto_dir}",
    f"--python_out={engine_root}",
    f"--grpc_python_out={engine_root}",
    str(proto_file),
])
print("Proto stubs generated in", engine_root)
