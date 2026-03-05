# ── Build stage: generate protobuf stubs ───────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy generated stubs + application code from builder
COPY --from=builder /app/avatar_pb2.py .
COPY --from=builder /app/avatar_pb2_grpc.py .
COPY main.py .
COPY worker.py .
COPY ml_pipeline.py .

EXPOSE 50051
EXPOSE 8000

ENV GRPC_PORT=50051
ENV PORT=8000
ENV AVATAR_STORAGE_BASE=https://storage.vfr.dev/models
# Disable buffering for cleaner logs
ENV PYTHONUNBUFFERED=1 

# We will let AppHost or docker-compose decide the entrypoint if it's the worker.
# Defaults to running the API (main.py which spins up both FastAPI and gRPC)
CMD ["python", "main.py"]
