from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from app.models import Submission

admin_bp = Blueprint("admin", __name__, url_prefix="/staff")


@admin_bp.route("/submissions")
@login_required
def submissions():
    if not (current_user.is_staff or current_user.is_admin):
        abort(403)

    recent_submissions = Submission.query.order_by(Submission.created_at.desc()).limit(50).all()
    return render_template("admin/submissions.html", submissions=recent_submissions)
