from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import LoginForm
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user)
            flash("Logged in successfully.", "success")
            next_url = request.args.get("next")
            if next_url and _is_safe_redirect(next_url):
                return redirect(next_url)
            return redirect(url_for("main.index"))

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


def _is_safe_redirect(target: str) -> bool:
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc and target.startswith("/")
