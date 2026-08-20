from __future__ import annotations

import asyncio
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from app.ingestion.base_collector import BaseCollector, CollectionJob, FetchedPayload


_UPLOAD_TYPES = {
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
}


class UploadCollector(BaseCollector):
    def __init__(self, *args, s3_client: Any, upload_bucket: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._s3 = s3_client
        self._upload_bucket = upload_bucket

    async def fetch(self, job: CollectionJob) -> FetchedPayload:
        if job.tenant_id is None:
            raise ValueError("Tenant ID is required for private uploads")
        parsed = urlsplit(job.source_url)
        key = parsed.path.lstrip("/")
        expected_prefix = f"tenant/{job.tenant_id}/uploads/"
        if parsed.scheme != "s3" or parsed.netloc != self._upload_bucket:
            raise ValueError("Upload must reference the configured private-upload bucket")
        if not key.startswith(expected_prefix):
            raise ValueError("Upload key is outside the authenticated tenant prefix")
        suffix = PurePosixPath(key).suffix.lower()
        if suffix not in _UPLOAD_TYPES:
            raise ValueError("Private upload type is not supported")
        response = await asyncio.to_thread(
            self._s3.get_object,
            Bucket=self._upload_bucket,
            Key=key,
        )
        body = await asyncio.to_thread(response["Body"].read)
        return FetchedPayload(
            body=body,
            content_type=response.get("ContentType") or _UPLOAD_TYPES[suffix],
            extension=suffix.lstrip("."),
            source_url=job.source_url,
            metadata={"tenant-id": str(job.tenant_id)},
        )
