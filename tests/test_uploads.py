from pathlib import Path
from io import BytesIO

from app.extensions import db
from app.models import AuditEvent, HandoffStatus, Submission, SubmissionFile


def test_multi_file_upload_creates_submission_records(client, login, app):
    login()
    response = client.post(
        "/upload",
        data={
            "lab_name": "North Lab",
            "batch_id": "B-100",
            "notes": "Morning run",
            "files": [
                (BytesIO(Path(__file__).read_bytes()), "results1.csv"),
                (BytesIO(b"header,value\n1,2\n"), "results2.xlsx"),
            ],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Upload successful. 2 file(s) received." in response.data
    assert b"Upload results" in response.data

    with app.app_context():
        submission = Submission.query.one()
        assert submission.lab_name == "North Lab"
        assert submission.batch_id == "B-100"
        assert SubmissionFile.query.count() == 2
        assert AuditEvent.query.filter_by(event_type="file_received").count() == 2
        assert AuditEvent.query.filter_by(event_type="handoff_queued").count() == 2
        assert SubmissionFile.query.filter_by(handoff_status=HandoffStatus.QUEUED.value).count() == 2


def test_disallowed_extension_is_rejected(client, login, app):
    login()
    response = client.post(
        "/upload",
        data={"files": [(BytesIO(b"abc"), "malware.exe")]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"No files were accepted" in response.data
    assert b"malware.exe" in response.data
    assert b"not allowed" in response.data

    with app.app_context():
        assert Submission.query.count() == 1
        assert SubmissionFile.query.count() == 0
        assert AuditEvent.query.filter_by(event_type="file_rejected").count() == 1


def test_duplicate_checksum_is_rejected(client, login, app):
    login()
    payload = b"same-content"
    first = client.post(
        "/upload",
        data={"files": [(BytesIO(payload), "first.csv")]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    second = client.post(
        "/upload",
        data={"files": [(BytesIO(payload), "second.csv")]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert b"Duplicate file detected" in second.data

    with app.app_context():
        assert Submission.query.count() == 2
        assert SubmissionFile.query.count() == 1
        assert AuditEvent.query.filter_by(event_type="duplicate_rejected").count() == 1


def test_staff_view_requires_staff_role(client, login):
    login(email="basic@example.com")
    response = client.get("/staff/submissions", follow_redirects=True)
    assert response.status_code == 200
    assert b"You do not have permission" in response.data


def test_oversized_upload_is_rejected(client, login, app):
    app.config["MAX_CONTENT_LENGTH"] = 10
    login()
    response = client.post(
        "/upload",
        data={"files": [(BytesIO(b"this-is-too-large"), "large.csv")]},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 413


def test_handoff_manifest_written(client, login, app):
    login()
    client.post(
        "/upload",
        data={"files": [(BytesIO(b"manifest-test"), "manifest.csv")]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with app.app_context():
        file_record = SubmissionFile.query.one()
        handoff_root = Path(app.config["HANDOFF_STAGING_ROOT"])
        manifest_path = handoff_root / f"submission-file-{file_record.id}.json"
        assert manifest_path.exists()


def test_admin_page_lists_submissions(client, login):
    login(email="admin@example.com")
    response = client.get("/staff/submissions")
    assert response.status_code == 200
    assert b"Recent submissions" in response.data
