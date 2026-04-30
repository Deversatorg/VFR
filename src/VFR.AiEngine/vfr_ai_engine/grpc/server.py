"""Legacy gRPC avatar service hosted beside the FastAPI process."""

from __future__ import annotations

from concurrent import futures
import logging
import os

import grpc

import avatar_pb2
import avatar_pb2_grpc

logger = logging.getLogger(__name__)


class AvatarServiceServicer(avatar_pb2_grpc.AvatarServiceServicer):
    """Return deterministic avatar URLs for the legacy gRPC surface."""

    _STORAGE_BASE = os.getenv("AVATAR_STORAGE_BASE", "https://storage.vfr.dev/models")

    def GenerateAvatar(self, request: avatar_pb2.AvatarRequest, context: grpc.ServicerContext) -> avatar_pb2.AvatarResponse:
        logger.info(
            "gRPC GenerateAvatar: user=%s body_type=%s h=%.1f w=%.1f",
            request.user_id,
            request.body_type,
            request.height_cm,
            request.weight_kg,
        )

        body_slug = (request.body_type or "regular").lower()
        model_id = f"{request.user_id}_{body_slug}"
        avatar_url = f"{self._STORAGE_BASE}/{model_id}.glb"

        return avatar_pb2.AvatarResponse(avatar_url=avatar_url, model_id=model_id)


def serve_grpc() -> None:
    port = int(os.getenv("GRPC_PORT", "50051"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    avatar_pb2_grpc.add_AvatarServiceServicer_to_server(AvatarServiceServicer(), server)
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    logger.info("VFR.AiEngine gRPC server listening on %s", listen_addr)
    server.start()
    server.wait_for_termination()

