from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Exam, StudyPlan, Topic
from app.services.planning import generate_study_plans

exam_bp = Blueprint("exam", __name__)


@exam_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_exam():
    if request.method == "POST":
        exam_date_raw = request.form.get("exam_date")
        daily_minutes = request.form.get("daily_minutes", type=int)
        weekend_minutes = request.form.get("weekend_minutes", type=int)
        excluded_weekdays = [int(x) for x in request.form.getlist("excluded_weekdays")]

        if not exam_date_raw or not daily_minutes or not weekend_minutes:
            flash("필수 입력값을 확인하세요.", "danger")
            return render_template("exam/new.html")

        try:
            exam_date = datetime.strptime(exam_date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("시험일 형식이 올바르지 않습니다.", "danger")
            return render_template("exam/new.html")

        exam = Exam(
            user_id=current_user.id,
            exam_date=exam_date,
            daily_minutes=daily_minutes,
            weekend_minutes=weekend_minutes,
            excluded_weekdays=excluded_weekdays,
        )
        db.session.add(exam)
        db.session.commit()

        topics = Topic.query.order_by(Topic.weight.desc()).all()
        try:
            plans = generate_study_plans(exam, topics)
            StudyPlan.query.filter_by(exam_id=exam.id).delete()
            db.session.add_all(plans)
            db.session.commit()
            flash(f"학습 계획 생성 완료: 총 {len(plans)}개 일정", "success")
            return redirect(url_for("exam.plan"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")

    return render_template("exam/new.html")


@exam_bp.route("/plan")
@login_required
def plan():
    plans = (
        StudyPlan.query.filter_by(user_id=current_user.id)
        .order_by(StudyPlan.plan_date.asc())
        .all()
    )

    grouped = {}
    for p in plans:
        grouped.setdefault(p.week_no, []).append(p)

    return render_template("plan/index.html", grouped=grouped)
