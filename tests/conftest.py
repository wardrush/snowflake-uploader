from io import BytesIO
from pathlib import Path

import pytest

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app(tmp_path: Path):
    app = create_app("testing")
    app.config.update(
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'test.db'}",
        UPLOAD_ROOT=str(tmp_path / "uploads"),
        HANDOFF_STAGING_ROOT=str(tmp_path / "handoff"),
        SERVER_NAME="localhost",
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(email="staff@example.com", is_staff=True, is_admin=False)
        user.set_password("password123")
        admin = User(email="admin@example.com", is_staff=True, is_admin=True)
        admin.set_password("password123")
        basic = User(email="basic@example.com", is_staff=False, is_admin=False)
        basic.set_password("password123")
        db.session.add_all([user, admin, basic])
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def login(client):
    def _login(email="staff@example.com", password="password123"):
        return client.post(
            "/auth/login",
            data={"email": email, "password": password},
            follow_redirects=True,
        )

    return _login


def make_upload(filename: str, content: bytes, content_type: str = "application/octet-stream"):
    return BytesIO(content), filename, content_type
