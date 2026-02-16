"""
S3 / MinIO storage adapter for registry blob storage.

Requires ``boto3`` (optional dependency).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .base import BaseStorageAdapter

logger = logging.getLogger("aquilia.mlops.registry.storage.s3")


class S3StorageAdapter(BaseStorageAdapter):
    """
    Store blobs in an S3-compatible bucket.

    Usage::

        adapter = S3StorageAdapter(
            bucket="my-modelpacks",
            endpoint_url="http://localhost:9000",  # for MinIO
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
        )
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "blobs/",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        self.bucket = bucket
        self.prefix = prefix
        self._endpoint_url = endpoint_url
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._region_name = region_name
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError(
                    "S3StorageAdapter requires boto3. Install with: pip install boto3"
                )
            kwargs = {"region_name": self._region_name}
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            if self._aws_access_key_id:
                kwargs["aws_access_key_id"] = self._aws_access_key_id
            if self._aws_secret_access_key:
                kwargs["aws_secret_access_key"] = self._aws_secret_access_key
            self._client = boto3.client("s3", **kwargs)
        return self._client

    def _key(self, digest: str) -> str:
        algo, hex_hash = digest.split(":", 1)
        return f"{self.prefix}{algo}/{hex_hash[:2]}/{hex_hash}"

    async def put_blob(self, digest: str, data: bytes) -> str:
        key = self._key(digest)
        self._get_client().put_object(Bucket=self.bucket, Key=key, Body=data)
        uri = f"s3://{self.bucket}/{key}"
        logger.info("Stored blob in S3: %s", uri)
        return uri

    async def get_blob(self, digest: str) -> bytes:
        key = self._key(digest)
        resp = self._get_client().get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    async def has_blob(self, digest: str) -> bool:
        key = self._key(digest)
        try:
            self._get_client().head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    async def delete_blob(self, digest: str) -> None:
        key = self._key(digest)
        self._get_client().delete_object(Bucket=self.bucket, Key=key)

    async def list_blobs(self) -> List[str]:
        paginator = self._get_client().get_paginator("list_objects_v2")
        digests: List[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                parts = key.replace(self.prefix, "").split("/")
                if len(parts) >= 3:
                    algo, _prefix, hex_hash = parts[0], parts[1], parts[2]
                    digests.append(f"{algo}:{hex_hash}")
        return digests
