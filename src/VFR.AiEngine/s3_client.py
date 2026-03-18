"""
S3 client singleton for VFR AI Engine.
Reads credentials from environment variables (injected by .env or Aspire).
Supports Backblaze B2 and any S3-compatible storage.
"""
import os
import logging
import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()  # reads .env when running locally; no-op inside Aspire (env vars injected)

logger = logging.getLogger("S3Client")

_S3_ENDPOINT   = os.getenv("S3_ENDPOINT_URL", "")
_S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
_S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "vfr-3d-assets")

# Public base URL for building asset URLs after upload.
# Some Backblaze configurations require /file/ bucket names, but direct endpoint URLs
# usually follow: <endpoint>/<bucket>/<key>
# Strip trailing slash from endpoint to normalise.
S3_PUBLIC_BASE = f"{_S3_ENDPOINT.rstrip('/')}/{S3_BUCKET_NAME}"


def _make_client():
    if not all([_S3_ENDPOINT, _S3_ACCESS_KEY, _S3_SECRET_KEY]):
        logger.warning(
            "S3 credentials not configured (S3_ENDPOINT_URL / S3_ACCESS_KEY / S3_SECRET_KEY). "
            "Uploads will be skipped and local URLs returned instead."
        )
        return None
    try:
        client = boto3.client(
            "s3",
            endpoint_url=_S3_ENDPOINT,
            aws_access_key_id=_S3_ACCESS_KEY,
            aws_secret_access_key=_S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),  # required by Backblaze B2
        )
        logger.info(f"S3 client initialised → {_S3_ENDPOINT} / bucket={S3_BUCKET_NAME}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialise S3 client: {e}")
        return None


# Module-level singleton — created once when the worker imports this module
s3_client = _make_client()


def upload_glb(local_path: str, s3_key: str) -> str:
    """
    Uploads a local .glb file to S3 and returns the public URL.

    Args:
        local_path: Absolute path to the .glb file on disk.
        s3_key:     Key (path) inside the bucket, e.g. "avatars/profile_uuid.glb".

    Returns:
        Public HTTPS URL to the uploaded file, or a fallback local path.
    """
    if s3_client is None:
        logger.warning(f"S3 unavailable — returning local path: {local_path}")
        return local_path

    try:
        logger.info(f"Uploading {local_path} → s3://{S3_BUCKET_NAME}/{s3_key}")
        with open(local_path, "rb") as f:
            s3_client.upload_fileobj(
                f,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    "ContentType": "model/gltf-binary",
                    "ACL": "public-read",           # make the file publicly accessible
                },
            )
        public_url = f"{S3_PUBLIC_BASE}/{s3_key}"
        logger.info(f"Upload successful: {public_url}")
        return public_url
    except Exception as e:
        logger.error(f"S3 upload failed for {s3_key}: {e}")
        raise


def delete_old_user_avatars(user_id: str):
    """
    Deletes any existing objects in the bucket that start with avatars/profile_{user_id}_.
    This prevents old timestamped models from accumulating in the bucket.
    """
    if s3_client is None:
        logger.warning(f"S3 client not initialized. Skipping cleanup for user {user_id}.")
        return

    prefix = f"avatars/profile_{user_id}_"
    logger.info(f"Cleaning up old avatars for user {user_id} with prefix: {prefix}")
    
    try:
        # List all objects with the given prefix
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        
        objects_to_delete = response.get('Contents', [])
        if not objects_to_delete:
            logger.info(f"No old avatars found for user {user_id}.")
            return

        for obj in objects_to_delete:
            key = obj['Key']
            try:
                s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
                logger.info(f"Successfully deleted old avatar: {key}")
            except Exception as del_e:
                logger.error(f"Failed to delete individual object {key}: {str(del_e)}")

    except Exception as e:
        logger.error(f"Failed to list or delete old avatars for user {user_id}: {str(e)}")
