from __future__ import annotations

from datetime import datetime, UTC
from enum import StrEnum

from flask_login import UserMixin
from sqlalchemy import Index
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


def utcnow() -> datetime:
    return datetime.now(UTC)


class SubmissionStatus(StrEnum):
    RECEIVED = "received"
    PARTIAL = "partial"
    FAILED = "failed"


class FileUploadStatus(StrEnum):
    RECEIVED = "received"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    ERROR = "error"


class HandoffStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    FAILED = "failed"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_staff = db.Column(db.Boolean, nullable=False, default=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    submissions = db.relationship("Submission", back_populates="user", lazy="dynamic")
    uploaded_files = db.relationship("SubmissionFile", back_populates="uploader", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    lab_name = db.Column(db.String(255), nullable=True)
    batch_id = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default=SubmissionStatus.RECEIVED.value, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="submissions")
    files = db.relationship(
        "SubmissionFile",
        back_populates="submission",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="SubmissionFile.uploaded_at.desc()",
    )
    audit_events = db.relationship("AuditEvent", back_populates="submission", lazy="select")


class SubmissionFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=False, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    storage_backend = db.Column(db.String(64), nullable=False)
    storage_path = db.Column(db.String(500), nullable=False)
    content_type = db.Column(db.String(255), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False)
    checksum_sha256 = db.Column(db.String(64), unique=True, nullable=False)
    file_ext = db.Column(db.String(16), nullable=False)
    upload_status = db.Column(db.String(32), nullable=False, default=FileUploadStatus.RECEIVED.value, index=True)
    handoff_status = db.Column(db.String(32), nullable=False, default=HandoffStatus.PENDING.value, index=True)
    error_message = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    handoff_at = db.Column(db.DateTime(timezone=True), nullable=True)

    submission = db.relationship("Submission", back_populates="files")
    uploader = db.relationship("User", back_populates="uploaded_files")
    audit_events = db.relationship("AuditEvent", back_populates="submission_file", lazy="select")

    __table_args__ = (
        Index("ix_submission_file_submission_created", "submission_id", "uploaded_at"),
    )


class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=True, index=True)
    submission_file_id = db.Column(db.Integer, db.ForeignKey("submission_file.id"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    remote_addr = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    submission = db.relationship("Submission", back_populates="audit_events")
    submission_file = db.relationship("SubmissionFile", back_populates="audit_events")

