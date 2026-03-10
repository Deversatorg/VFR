# ── Build stage: install deps and generate protobuf stubs ──────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Step 1: Install HEAVY packages first (torch, smplx) in their own layer.
# Docker caches this layer aggressively — only rebuilt if requirements change.
# This prevents the build from timing out on every restart.
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install remaining packages (much faster)
RUN pip install --no-cache-dir \
    grpcio==1.62.2 \
    grpcio-tools==1.62.2 \
    protobuf==4.25.3 \
    fastapi==0.111.0 \
    uvicorn==0.29.0 \
    pydantic==2.7.1 \
    celery==5.4.0 \
    redis==5.0.4 \
    python-multipart==0.0.9 \
    smplx \
    trimesh==4.4.0 \
    scipy==1.13.0 \
    numpy==1.26.4 \
    "pygltflib>=1.16.5" \
    "rembg>=2.0.57" \
    "Pillow>=10.3.0"

# Copy proto file and generate Python stubs
COPY avatar.proto ./avatar.proto
RUN python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    avatar.proto

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder (avoids reinstalling)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy generated stubs + application code
COPY --from=builder /app/avatar_pb2.py .
COPY --from=builder /app/avatar_pb2_grpc.py .
COPY main.py .
COPY worker.py .
COPY ml_pipeline.py .
COPY garment_pipeline.py .
COPY models/ models/

EXPOSE 50051
EXPOSE 8000

ENV GRPC_PORT=50051
ENV PORT=8000
ENV AVATAR_STORAGE_BASE=https://storage.vfr.dev/models
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
