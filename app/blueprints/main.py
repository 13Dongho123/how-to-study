from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models import Quiz, StudyPlan, WrongAnswer

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def dashboard():
    if not current_user.is_authenticated:
        return render_template("index_guest.html")

    upcoming_plans = (
        StudyPlan.query.filter_by(user_id=current_user.id)
        .order_by(StudyPlan.plan_date.asc())
        .limit(7)
        .all()
    )
    recent_quizzes = (
        Quiz.query.filter_by(user_id=current_user.id)
        .order_by(Quiz.created_at.desc())
        .limit(5)
        .all()
    )
    wrong_count = WrongAnswer.query.filter_by(user_id=current_user.id, mastered=False).count()

    return render_template(
        "dashboard.html",
        upcoming_plans=upcoming_plans,
        recent_quizzes=recent_quizzes,
        wrong_count=wrong_count,
    )


@main_bp.route("/plan")
@login_required
def plan_view():
    plans = (
        StudyPlan.query.filter_by(user_id=current_user.id)
        .order_by(StudyPlan.plan_date.asc())
        .all()
    )

    grouped = {}
    for p in plans:
        grouped.setdefault(p.week_no, []).append(p)

    return render_template("plan/index.html", grouped=grouped)
