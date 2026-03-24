from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.models import HandoffStatus, SubmissionFile, utcnow


@dataclass
class HandoffResult:
    status: str
    error_message: str | None = None


class HandoffService:
    def handoff(self, submission_file: SubmissionFile) -> HandoffResult:
        raise NotImplementedError


class DatabaseQueueHandoffService(HandoffService):
    def __init__(self, staging_root: str):
        self.staging_root = Path(staging_root)
        self.staging_root.mkdir(parents=True, exist_ok=True)

    def handoff(self, submission_file: SubmissionFile) -> HandoffResult:
        manifest = {
            "submission_file_id": submission_file.id,
            "submission_id": submission_file.submission_id,
            "uploader_id": submission_file.uploader_id,
            "storage_path": submission_file.storage_path,
            "checksum_sha256": submission_file.checksum_sha256,
            "content_type": submission_file.content_type,
            "size_bytes": submission_file.size_bytes,
            "uploaded_at": submission_file.uploaded_at.isoformat(),
        }

        manifest_path = self.staging_root / f"submission-file-{submission_file.id}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        submission_file.handoff_status = HandoffStatus.QUEUED.value
        submission_file.handoff_at = utcnow()
        return HandoffResult(status=HandoffStatus.QUEUED.value)
