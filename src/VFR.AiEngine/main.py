"""
VFR.AiEngine — gRPC Avatar Generation Service
Phase 3 MVP: deterministic avatar URLs based on body measurements.
Phase 4+: replace body of GenerateAvatar with a real ML pipeline.
"""

import grpc
from concurrent import futures
import os
import logging

import avatar_pb2
import avatar_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AvatarServiceServicer(avatar_pb2_grpc.AvatarServiceServicer):
    """
    MVP implementation: returns a stable CDN URL based on user_id + body_type.
    TODO Phase 4: call a mesh-generation model (e.g. SMPL-X) to produce a real .glb.
    """

    # Base storage URL — override with AVATAR_STORAGE_BASE env var in production.
    _STORAGE_BASE = os.getenv("AVATAR_STORAGE_BASE", "https://storage.vfr.dev/models")

    def GenerateAvatar(
        self, request: avatar_pb2.AvatarRequest, context: grpc.ServicerContext
    ) -> avatar_pb2.AvatarResponse:
        logger.info(
            "GenerateAvatar: user=%s body_type=%s h=%.1f w=%.1f",
            request.user_id,
            request.body_type,
            request.height_cm,
            request.weight_kg,
        )

        # Deterministic model ID derived from user_id and body_type (MVP stub).
        # Replace with ML model call in Phase 4.
        body_slug = (request.body_type or "regular").lower()
        model_id = f"{request.user_id}_{body_slug}"
        avatar_url = f"{self._STORAGE_BASE}/{model_id}.glb"

        return avatar_pb2.AvatarResponse(
            avatar_url=avatar_url,
            model_id=model_id,
        )


def serve() -> None:
    port = int(os.getenv("GRPC_PORT", "50051"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    avatar_pb2_grpc.add_AvatarServiceServicer_to_server(AvatarServiceServicer(), server)
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    logger.info("VFR.AiEngine gRPC server listening on %s", listen_addr)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
