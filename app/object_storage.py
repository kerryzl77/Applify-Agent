"""Artifact storage adapter with local and S3 backends."""

from __future__ import annotations

import logging
import mimetypes
import shutil
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class ObjectStorage:
    """Persist artifacts to local disk in development and S3 in production."""

    def __init__(self):
        self.settings = get_settings()
        self.backend = self.settings.artifact_storage_backend
        self.local_root = Path(self.settings.artifact_storage_local_root).resolve()
        self.local_root.mkdir(parents=True, exist_ok=True)
        self._s3_client = None

    def store_file(
        self,
        local_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Store an on-disk file and return storage metadata."""
        filepath = Path(local_path)
        if not filepath.exists():
            raise FileNotFoundError(local_path)
        resolved_content_type = (
            content_type
            or mimetypes.guess_type(filepath.name)[0]
            or "application/octet-stream"
        )
        if self.backend == "s3":
            return self._store_file_s3(filepath, object_key, resolved_content_type, metadata or {})
        return self._store_file_local(filepath, object_key, resolved_content_type)

    def download_bytes(self, artifact: dict) -> bytes:
        """Read artifact bytes from configured storage backend."""
        backend = artifact.get("storage_backend") or "local"
        if backend == "s3":
            return self._download_bytes_s3(artifact)
        object_key = artifact.get("object_key")
        if not object_key:
            raise FileNotFoundError("Artifact object key missing")
        return (self.local_root / object_key).read_bytes()

    def _store_file_local(self, filepath: Path, object_key: str, content_type: str) -> dict:
        destination = self.local_root / object_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(filepath, destination)
        return {
            "storage_backend": "local",
            "bucket_name": None,
            "object_key": object_key,
            "filename": filepath.name,
            "content_type": content_type,
            "size_bytes": destination.stat().st_size,
        }

    def _store_file_s3(self, filepath: Path, object_key: str, content_type: str, metadata: dict) -> dict:
        client = self._get_s3_client()
        bucket_name = self.settings.s3_bucket_name
        if not bucket_name:
            raise RuntimeError("S3 storage selected but S3_BUCKET_NAME is not configured")
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = {str(k): str(v) for k, v in metadata.items()}
        client.upload_file(str(filepath), bucket_name, object_key, ExtraArgs=extra_args)
        return {
            "storage_backend": "s3",
            "bucket_name": bucket_name,
            "object_key": object_key,
            "filename": filepath.name,
            "content_type": content_type,
            "size_bytes": filepath.stat().st_size,
        }

    def _download_bytes_s3(self, artifact: dict) -> bytes:
        client = self._get_s3_client()
        bucket_name = artifact.get("bucket_name") or self.settings.s3_bucket_name
        object_key = artifact.get("object_key")
        if not bucket_name or not object_key:
            raise FileNotFoundError("Incomplete S3 artifact metadata")
        response = client.get_object(Bucket=bucket_name, Key=object_key)
        return response["Body"].read()

    def _get_s3_client(self):
        if self._s3_client is not None:
            return self._s3_client
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 artifact storage") from exc

        session = boto3.session.Session()
        self._s3_client = session.client(
            "s3",
            region_name=self.settings.s3_region,
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
        )
        logger.info("Initialized S3 artifact storage client")
        return self._s3_client
