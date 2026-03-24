from __future__ import annotations

from dataclasses import dataclass

from flask import Flask
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    AuditEvent,
    FileUploadStatus,
    HandoffStatus,
    Submission,
    SubmissionFile,
    SubmissionStatus,
    User,
)
from app.services.handoff_service import DatabaseQueueHandoffService, HandoffService
from app.services.storage_service import LocalStorageService, StorageService


@dataclass
class UploadOutcome:
    filename: str
    status: str
    message: str
    submission_file_id: int | None = None


@dataclass
class SubmissionResult:
    submission: Submission
    outcomes: list[UploadOutcome]

    @property
    def accepted_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.status == FileUploadStatus.RECEIVED.value)

    @property
    def summary_message(self) -> str:
        total = len(self.outcomes)
        accepted = self.accepted_count
        if total == 0:
            return "No files were accepted. Review the file-specific messages."
        if accepted == total:
            return f"Upload successful. {accepted} file(s) received."
        if accepted == 0:
            return "No files were accepted. Review the file-specific messages."
        return f"{accepted} of {total} file(s) were accepted."


class UploadService:
    def __init__(self, storage_service: StorageService, handoff_service: HandoffService, allowed_extensions: tuple[str, ...]):
        self.storage_service = storage_service
        self.handoff_service = handoff_service
        self.allowed_extensions = {ext.lower() for ext in allowed_extensions}

    @classmethod
    def from_app(cls, app: Flask) -> "UploadService":
        storage_service = LocalStorageService(app.config["UPLOAD_ROOT"])
        handoff_service = DatabaseQueueHandoffService(app.config["HANDOFF_STAGING_ROOT"])
        return cls(storage_service, handoff_service, app.config["ALLOWED_EXTENSIONS"])

    def process_submission(
        self,
        uploader: User,
        files: list[FileStorage],
        lab_name: str | None,
        batch_id: str | None,
        notes: str | None,
        remote_addr: str | None,
    ) -> SubmissionResult:
        submission = Submission(
            user_id=uploader.id,
            lab_name=self._clean_optional(lab_name),
            batch_id=self._clean_optional(batch_id),
            notes=self._clean_optional(notes),
            status=SubmissionStatus.RECEIVED.value,
        )
        db.session.add(submission)
        db.session.flush()

        outcomes: list[UploadOutcome] = []
        accepted_count = 0

        for file_storage in files:
            filename = file_storage.filename or "unnamed-file"
            if not filename:
                continue

            safe_filename = secure_filename(filename)
            ext = self._extension_for(safe_filename)
            if ext not in self.allowed_extensions:
                message = f"File type {ext or 'unknown'} is not allowed."
                outcomes.append(UploadOutcome(filename=filename, status=FileUploadStatus.REJECTED.value, message=message))
                self._create_audit_event(
                    uploader.id,
                    submission.id,
                    None,
                    "file_rejected",
                    f"{filename}: {message}",
                    remote_addr,
                )
                continue

            try:
                stored_file = self.storage_service.save_upload(file_storage, destination_hint="incoming")
            except Exception as exc:
                message = f"Upload failed while storing the file: {exc}"
                outcomes.append(UploadOutcome(filename=filename, status=FileUploadStatus.ERROR.value, message=message))
                self._create_audit_event(
                    uploader.id,
                    submission.id,
                    None,
                    "storage_failed",
                    f"{filename}: {message}",
                    remote_addr,
                )
                continue

            existing = SubmissionFile.query.filter_by(checksum_sha256=stored_file.checksum_sha256).first()
            if existing:
                if hasattr(self.storage_service, "delete"):
                    self.storage_service.delete(stored_file.storage_path)
                message = "Duplicate file detected. This file has already been uploaded."
                outcomes.append(UploadOutcome(filename=filename, status=FileUploadStatus.DUPLICATE.value, message=message))
                self._create_audit_event(
                    uploader.id,
                    submission.id,
                    None,
                    "duplicate_rejected",
                    f"{filename}: {message}",
                    remote_addr,
                )
                continue

            submission_file = SubmissionFile(
                submission_id=submission.id,
                uploader_id=uploader.id,
                original_filename=stored_file.original_filename,
                stored_name=stored_file.stored_name,
                storage_backend=stored_file.storage_backend,
                storage_path=stored_file.storage_path,
                content_type=stored_file.content_type,
                size_bytes=stored_file.size_bytes,
                checksum_sha256=stored_file.checksum_sha256,
                file_ext=stored_file.file_ext,
                upload_status=FileUploadStatus.RECEIVED.value,
                handoff_status=HandoffStatus.PENDING.value,
            )
            db.session.add(submission_file)
            db.session.flush()

            self._create_audit_event(
                uploader.id,
                submission.id,
                submission_file.id,
                "file_received",
                f"{filename} received and stored.",
                remote_addr,
            )

            try:
                handoff_result = self.handoff_service.handoff(submission_file)
            except Exception as exc:
                handoff_result = None
                submission_file.handoff_status = HandoffStatus.FAILED.value
                submission_file.error_message = str(exc)
                self._create_audit_event(
                    uploader.id,
                    submission.id,
                    submission_file.id,
                    "handoff_failed",
                    f"{filename}: {exc}",
                    remote_addr,
                )
            if handoff_result and handoff_result.error_message:
                submission_file.handoff_status = HandoffStatus.FAILED.value
                submission_file.error_message = handoff_result.error_message
                self._create_audit_event(
                    uploader.id,
                    submission.id,
                    submission_file.id,
                    "handoff_failed",
                    f"{filename}: {handoff_result.error_message}",
                    remote_addr,
                )
            elif handoff_result:
                self._create_audit_event(
                    uploader.id,
                    submission.id,
                    submission_file.id,
                    "handoff_queued",
                    f"{filename} queued for downstream processing.",
                    remote_addr,
                )

            accepted_count += 1
            outcomes.append(
                UploadOutcome(
                    filename=filename,
                    status=submission_file.upload_status,
                    message="Received successfully.",
                    submission_file_id=submission_file.id,
                )
            )

        submission.status = self._submission_status_for(outcomes, accepted_count)
        db.session.commit()
        return SubmissionResult(submission=submission, outcomes=outcomes)

    def _clean_optional(self, value: str | None) -> str | None:
        if not value:
            return None
        stripped = value.strip()
        return stripped or None

    def _extension_for(self, filename: str) -> str:
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()

    def _submission_status_for(self, outcomes: list[UploadOutcome], accepted_count: int) -> str:
        if not outcomes or accepted_count == 0:
            return SubmissionStatus.FAILED.value
        if accepted_count < len(outcomes):
            return SubmissionStatus.PARTIAL.value
        return SubmissionStatus.RECEIVED.value

    def _create_audit_event(
        self,
        user_id: int | None,
        submission_id: int | None,
        submission_file_id: int | None,
        event_type: str,
        message: str,
        remote_addr: str | None,
    ) -> None:
        db.session.add(
            AuditEvent(
                user_id=user_id,
                submission_id=submission_id,
                submission_file_id=submission_file_id,
                event_type=event_type,
                message=message,
                remote_addr=remote_addr,
            )
        )
