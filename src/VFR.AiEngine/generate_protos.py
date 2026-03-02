"""
Run this script once to (re)generate avatar_pb2.py and avatar_pb2_grpc.py
from the shared protos/avatar.proto definition.

Usage (from repo root):
    cd src/VFR.AiEngine
    pip install grpcio-tools
    python generate_protos.py
"""
import subprocess
import sys
from pathlib import Path

# Paths relative to this script's location (src/VFR.AiEngine)
script_dir = Path(__file__).parent
proto_dir  = script_dir.parent.parent / "protos"
proto_file = proto_dir / "avatar.proto"

subprocess.check_call([
    sys.executable, "-m", "grpc_tools.protoc",
    f"-I{proto_dir}",
    f"--python_out={script_dir}",
    f"--grpc_python_out={script_dir}",
    str(proto_file),
])
print("✅ Proto stubs generated in", script_dir)
