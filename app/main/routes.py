from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.forms import UploadForm
from app.models import Submission
from app.services.upload_service import UploadService

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    recent_submissions = (
        Submission.query.filter_by(user_id=current_user.id)
        .order_by(Submission.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template("main/index.html", recent_submissions=recent_submissions)


@main_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        upload_service = UploadService.from_app(current_app)
        result = upload_service.process_submission(
            uploader=current_user,
            files=request.files.getlist("files"),
            lab_name=form.lab_name.data,
            batch_id=form.batch_id.data,
            notes=form.notes.data,
            remote_addr=request.headers.get("X-Forwarded-For", request.remote_addr),
        )
        flash(result.summary_message, "success" if result.accepted_count else "error")
        session["submission_outcomes"] = [
            {
                "filename": outcome.filename,
                "status": outcome.status,
                "message": outcome.message,
                "submission_file_id": outcome.submission_file_id,
            }
            for outcome in result.outcomes
        ]
        return redirect(url_for("main.submission_detail", submission_id=result.submission.id))

    return render_template("main/upload.html", form=form)


@main_bp.route("/submissions/<int:submission_id>")
@login_required
def submission_detail(submission_id: int):
    submission = Submission.query.get_or_404(submission_id)
    if submission.user_id != current_user.id and not (current_user.is_staff or current_user.is_admin):
        abort(403)
    outcomes = session.pop("submission_outcomes", None)
    return render_template("main/submission_detail.html", submission=submission, outcomes=outcomes)
