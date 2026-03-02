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

EXPOSE 50051

ENV GRPC_PORT=50051
ENV AVATAR_STORAGE_BASE=https://storage.vfr.dev/models

ENTRYPOINT ["python", "main.py"]
