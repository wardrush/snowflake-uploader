import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.admin.routes import admin_bp
from app.auth.routes import auth_bp
from app.config import config_by_name
from app.extensions import csrf, db, login_manager, migrate
from app.forms import UploadForm
from app.main.routes import main_bp


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    selected_config = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_by_name[selected_config])

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["HANDOFF_STAGING_ROOT"]).mkdir(parents=True, exist_ok=True)

    if app.config.get("USE_PROXY_FIX"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # type: ignore[assignment]

    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)
    configure_logging(app)

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)


def register_error_handlers(app: Flask) -> None:
    from flask import flash, redirect, render_template, request, url_for

    @app.errorhandler(403)
    def forbidden(_error):
        flash("You do not have permission to access that page.", "error")
        return redirect(url_for("main.index"))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_error):
        if request.endpoint == "main.upload":
            form = UploadForm()
            flash("One or more files exceeded the maximum upload size.", "error")
            return render_template("main/upload.html", form=form), 413
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):
        flash(f"Security validation failed: {error.description}", "error")
        return redirect(url_for("auth.login"))


def configure_logging(app: Flask) -> None:
    if app.debug or app.testing:
        return

    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    app.logger.setLevel(log_level)

    if app.config.get("LOG_TO_STDOUT", True):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(logging.Formatter(app.config["LOG_FORMAT"]))
        app.logger.addHandler(stream_handler)

    log_file = app.config.get("LOG_FILE")
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_path, maxBytes=1_048_576, backupCount=5)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(app.config["LOG_FORMAT"]))
        app.logger.addHandler(file_handler)


def register_cli(app: Flask) -> None:
    from app.cli import register_commands

    register_commands(app)
