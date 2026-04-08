# ── VFR AI Engine Dockerfile ──────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Step 0: Install system dependencies required by Trimesh, Rembg, OpenCV, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Step 1: Install HEAVY packages first (torch).
# Docker caches this layer aggressively — only rebuilt if torch changes.
RUN pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu

# Step 2: Copy requirements and install the rest
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 3: Copy proto file and generate Python stubs
COPY avatar.proto ./avatar.proto
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. avatar.proto

# Step 4: Copy application code
COPY main.py worker.py logging_config.py ml_pipeline.py garment_pipeline.py s3_client.py anthropometry.py measurement_optimizer.py extract_vertex_loops.py ./
COPY models/ models/

EXPOSE 50051 8000

ENV GRPC_PORT=50051 \
    PORT=8000 \
    AVATAR_STORAGE_BASE=https://storage.vfr.dev/models \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
