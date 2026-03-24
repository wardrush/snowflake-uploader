from app.models import User


def test_create_user_command(runner, app):
    result = runner.invoke(
        args=[
            "create-user",
            "--email",
            "new@example.com",
            "--password",
            "password123",
            "--staff",
            "--admin",
        ]
    )

    assert result.exit_code == 0
    with app.app_context():
        user = User.query.filter_by(email="new@example.com").first()
        assert user is not None
        assert user.is_admin is True
