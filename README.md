# Lab File Intake App

This project is a small Flask web app for lab staff to log in, upload one or more lab files, and receive a clear confirmation that the files were recorded for later Snowflake-oriented ingestion.

It is intentionally simple:
- server-rendered Flask + Jinja
- SQLAlchemy models with Flask-Migrate
- Flask-Login sessions
- local filesystem storage abstraction by default
- downstream handoff abstraction that can later be swapped for Snowflake stage, S3, or Azure Blob integration

## Why this structure fits PythonAnywhere

The app uses a standard Flask app factory plus a `wsgi.py` entrypoint, avoids background workers, and relies on plain HTTP form posts and synchronous request handling. That keeps deployment aligned with PythonAnywhere’s WSGI model and reduces operational overhead.

The storage and handoff logic live behind dedicated service modules:
- [`app/services/storage_service.py`](/C:/Users/wardr/Downloads/codex-projects/snowflake_uploader/app/services/storage_service.py)
- [`app/services/handoff_service.py`](/C:/Users/wardr/Downloads/codex-projects/snowflake_uploader/app/services/handoff_service.py)

That keeps the web app focused on intake, auditability, and safe persistence while making later Snowflake integration a contained replacement rather than a rewrite.

## Project layout

```text
app/
  admin/
  auth/
  main/
  services/
  static/css/
  templates/
  __init__.py
  cli.py
  config.py
  extensions.py
  forms.py
  models.py
migrations/
tests/
manage.py
wsgi.py
requirements.txt
```

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update values as needed.
4. Initialize the database:

```bash
flask --app manage.py db upgrade
```

5. Create the first admin user:

```bash
flask --app manage.py create-user --email admin@example.com --password change-me --staff --admin
```

6. Run the app locally:

```bash
flask --app manage.py run
```

## Environment variables

Defined in [`.env.example`](/C:/Users/wardr/Downloads/codex-projects/snowflake_uploader/.env.example):

- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: SQLAlchemy database URL. SQLite works locally; PythonAnywhere MySQL can be used in production.
- `UPLOAD_ROOT`: root directory for stored uploads
- `HANDOFF_STAGING_ROOT`: root directory for downstream handoff manifests
- `MAX_CONTENT_LENGTH`: max request size in bytes
- `ALLOWED_EXTENSIONS`: comma-separated upload allowlist
- `SESSION_COOKIE_SECURE`: set `true` in HTTPS production
- `SESSION_COOKIE_SAMESITE`: cookie same-site policy
- `USE_PROXY_FIX`: enable only if proxy headers need to be trusted
- `LOG_LEVEL`, `LOG_TO_STDOUT`, `LOG_FILE`: logging controls

## Migrations

Alembic scaffolding and an initial migration are included.

To create a new migration after schema changes:

```bash
flask --app manage.py db migrate -m "describe change"
flask --app manage.py db upgrade
```

## Authentication and roles

- Any authenticated user can upload files and view their own submissions.
- Staff or admin users can view the shared submissions page.
- Passwords are hashed with Werkzeug.
- CSRF protection is enabled for normal app usage.

## Upload flow

1. User logs in.
2. User uploads one or more files and optional metadata.
3. Files are validated against the extension allowlist and request-size cap.
4. Files are stored via the storage service.
5. SHA-256 checksums are computed and checked for duplicates.
6. A `Submission` row is created for the user action.
7. A `SubmissionFile` row is created for each accepted file.
8. `AuditEvent` rows record receipt, rejection, duplicate detection, and handoff state.
9. The handoff service marks accepted files as queued and writes a manifest for later polling.

## PythonAnywhere deployment notes

1. Create a PythonAnywhere web app configured for Flask.
2. Upload the code to a project directory.
3. Create a virtualenv and install `requirements.txt`.
4. Set environment variables in PythonAnywhere or load them from a `.env` file stored outside version control.
5. Point the WSGI file at [`wsgi.py`](/C:/Users/wardr/Downloads/codex-projects/snowflake_uploader/wsgi.py) or import `application = create_app("production")`.
6. Set `DATABASE_URL` to a PythonAnywhere MySQL URL if moving off SQLite.
7. Set `UPLOAD_ROOT` and `HANDOFF_STAGING_ROOT` to writable directories owned by the web app user.
8. Run `flask --app manage.py db upgrade`.
9. Create the first admin with the CLI command.
10. Reload the web app from the PythonAnywhere dashboard.

Recommended production settings:
- set `SESSION_COOKIE_SECURE=true`
- use a strong `SECRET_KEY`
- point logging at a writable file or stdout-compatible destination
- use MySQL instead of SQLite for multi-user production usage

## Where to plug in Snowflake or object storage later

The first integration points are:
- [`app/services/storage_service.py`](/C:/Users/wardr/Downloads/codex-projects/snowflake_uploader/app/services/storage_service.py) for replacing local disk with S3/Azure Blob-backed storage
- [`app/services/handoff_service.py`](/C:/Users/wardr/Downloads/codex-projects/snowflake_uploader/app/services/handoff_service.py) for replacing the placeholder queue manifest with:
  - direct Snowflake stage upload
  - external stage object publication
  - a presigned-upload workflow

The web routes and templates should not need major changes when those services are swapped.

## Tests

Run:

```bash
pytest
```

The suite covers login, auth gating, multi-file upload, extension validation, duplicate detection, staff authorization, handoff manifest creation, and basic audit behavior.

## First production hardening steps

- Move production storage from local disk to durable object storage or a clearly managed persistent filesystem location.
- Replace SQLite with MySQL on PythonAnywhere.
- Add stronger operational logging and alerting around upload failures and downstream handoff failures.
- Add optional password reset and account management workflows if staff provisioning will be ongoing.
