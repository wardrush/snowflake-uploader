"""initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_staff", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    op.create_table(
        "submission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lab_name", sa.String(length=255), nullable=True),
        sa.Column("batch_id", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_submission_created_at"), "submission", ["created_at"], unique=False)
    op.create_index(op.f("ix_submission_status"), "submission", ["status"], unique=False)
    op.create_index(op.f("ix_submission_user_id"), "submission", ["user_id"], unique=False)

    op.create_table(
        "submission_file",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("uploader_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("storage_backend", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_ext", sa.String(length=16), nullable=False),
        sa.Column("upload_status", sa.String(length=32), nullable=False),
        sa.Column("handoff_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("handoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["submission_id"], ["submission.id"]),
        sa.ForeignKeyConstraint(["uploader_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checksum_sha256"),
    )
    op.create_index(op.f("ix_submission_file_handoff_status"), "submission_file", ["handoff_status"], unique=False)
    op.create_index(op.f("ix_submission_file_submission_id"), "submission_file", ["submission_id"], unique=False)
    op.create_index("ix_submission_file_submission_created", "submission_file", ["submission_id", "uploaded_at"], unique=False)
    op.create_index(op.f("ix_submission_file_uploaded_at"), "submission_file", ["uploaded_at"], unique=False)
    op.create_index(op.f("ix_submission_file_upload_status"), "submission_file", ["upload_status"], unique=False)
    op.create_index(op.f("ix_submission_file_uploader_id"), "submission_file", ["uploader_id"], unique=False)

    op.create_table(
        "audit_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("submission_file_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("remote_addr", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_file_id"], ["submission_file.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submission.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_event_created_at"), "audit_event", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_event_event_type"), "audit_event", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_event_submission_file_id"), "audit_event", ["submission_file_id"], unique=False)
    op.create_index(op.f("ix_audit_event_submission_id"), "audit_event", ["submission_id"], unique=False)
    op.create_index(op.f("ix_audit_event_user_id"), "audit_event", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_audit_event_user_id"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_submission_id"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_submission_file_id"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_event_type"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_created_at"), table_name="audit_event")
    op.drop_table("audit_event")

    op.drop_index(op.f("ix_submission_file_uploader_id"), table_name="submission_file")
    op.drop_index(op.f("ix_submission_file_upload_status"), table_name="submission_file")
    op.drop_index(op.f("ix_submission_file_uploaded_at"), table_name="submission_file")
    op.drop_index("ix_submission_file_submission_created", table_name="submission_file")
    op.drop_index(op.f("ix_submission_file_submission_id"), table_name="submission_file")
    op.drop_index(op.f("ix_submission_file_handoff_status"), table_name="submission_file")
    op.drop_table("submission_file")

    op.drop_index(op.f("ix_submission_user_id"), table_name="submission")
    op.drop_index(op.f("ix_submission_status"), table_name="submission")
    op.drop_index(op.f("ix_submission_created_at"), table_name="submission")
    op.drop_table("submission")

    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
