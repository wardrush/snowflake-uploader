import click
from flask import Flask

from app.extensions import db
from app.models import User


def register_commands(app: Flask) -> None:
    @app.cli.command("create-user")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--staff/--no-staff", default=True)
    @click.option("--admin/--no-admin", default=False)
    def create_user(email: str, password: str, staff: bool, admin: bool) -> None:
        existing = User.query.filter_by(email=email.lower()).first()
        if existing:
            raise click.ClickException("A user with that email already exists.")

        user = User(email=email.lower(), is_staff=staff or admin, is_admin=admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created user {user.email}.")
