from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Attempt, AttemptAnswer, Question, ReviewTask, WrongAnswer

review_bp = Blueprint("review", __name__)


def _normalize(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _is_correct(question: Question, user_answer: str) -> bool:
    correct = _normalize(question.answer)
    ans = _normalize(user_answer)
    if not ans:
        return False
    if question.type == "mcq":
        return ans == correct
    return ans == correct or correct in ans or ans in correct


@review_bp.route("/")
@login_required
def index():
    include_mastered = request.args.get("include_mastered", "0") == "1"

    query = WrongAnswer.query.filter_by(user_id=current_user.id)
    if not include_mastered:
        query = query.filter_by(mastered=False)

    wrong_items = query.order_by(
        WrongAnswer.mastered.asc(),
        WrongAnswer.wrong_count.desc(),
        WrongAnswer.last_wrong_at.desc(),
    ).all()

    return render_template(
        "review/index.html",
        wrong_items=wrong_items,
        include_mastered=include_mastered,
        today=date.today().isoformat(),
    )


@review_bp.route("/actions", methods=["POST"])
@login_required
def actions():
    action = request.form.get("action", "")
    question_ids = [int(qid) for qid in request.form.getlist("question_ids") if qid.isdigit()]
    include_mastered = request.form.get("include_mastered", "0") == "1"

    if not question_ids:
        flash("최소 1개 문제를 선택하세요.", "warning")
        return redirect(url_for("review.index", include_mastered="1" if include_mastered else "0"))

    wrong_items = WrongAnswer.query.filter(
        WrongAnswer.user_id == current_user.id,
        WrongAnswer.question_id.in_(question_ids),
    ).all()
    owned_qids = {w.question_id for w in wrong_items}

    if not owned_qids:
        flash("선택한 문제를 찾을 수 없습니다.", "warning")
        return redirect(url_for("review.index", include_mastered="1" if include_mastered else "0"))

    if action == "mark_mastered":
        updated = 0
        skipped = 0
        for w in wrong_items:
            if w.mastered:
                skipped += 1
                continue
            w.mastered = True
            updated += 1

        db.session.commit()
        flash(f"완료 처리: {updated}개, 이미 완료: {skipped}개", "success")

    elif action in {"schedule_today", "schedule_date"}:
        if action == "schedule_today":
            scheduled_date = date.today()
        else:
            raw = request.form.get("scheduled_date", "").strip()
            try:
                scheduled_date = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                flash("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)", "danger")
                return redirect(url_for("review.index", include_mastered="1" if include_mastered else "0"))

        existing = ReviewTask.query.filter(
            ReviewTask.user_id == current_user.id,
            ReviewTask.scheduled_date == scheduled_date,
            ReviewTask.question_id.in_(owned_qids),
        ).all()
        existing_qids = {x.question_id for x in existing}

        inserted = 0
        for qid in owned_qids:
            if qid in existing_qids:
                continue
            db.session.add(
                ReviewTask(
                    user_id=current_user.id,
                    question_id=qid,
                    scheduled_date=scheduled_date,
                    status="scheduled",
                )
            )
            inserted += 1

        db.session.commit()
        duplicate = len(owned_qids) - inserted
        flash(
            f"복습 일정 추가({scheduled_date}): {inserted}개, 중복 스킵: {duplicate}개",
            "success",
        )

    else:
        flash("지원하지 않는 액션입니다.", "danger")

    return redirect(url_for("review.index", include_mastered="1" if include_mastered else "0"))


@review_bp.route("/session", methods=["GET", "POST"])
@login_required
def session():
    wrong_items = (
        WrongAnswer.query.filter_by(user_id=current_user.id, mastered=False)
        .order_by(WrongAnswer.wrong_count.desc(), WrongAnswer.last_wrong_at.desc())
        .all()
    )
    questions = [w.question for w in wrong_items if w.question]

    if request.method == "POST":
        if not questions:
            flash("복습할 오답이 없습니다.", "info")
            return redirect(url_for("review.index"))

        attempt = Attempt(
            user_id=current_user.id,
            quiz_id=questions[0].quiz_id,
            is_review=True,
            total=len(questions),
            score=0,
        )
        db.session.add(attempt)
        db.session.flush()

        score = 0
        for q in questions:
            ua = request.form.get(f"q_{q.id}", "")
            ok = _is_correct(q, ua)
            db.session.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    question_id=q.id,
                    user_answer=ua,
                    is_correct=ok,
                )
            )

            wrong = WrongAnswer.query.filter_by(user_id=current_user.id, question_id=q.id).first()
            if not wrong:
                continue

            if ok:
                wrong.mastered = True
                score += 1
            else:
                wrong.wrong_count += 1
                wrong.last_wrong_at = datetime.utcnow()
                wrong.mastered = False

        attempt.score = score
        db.session.commit()
        flash(f"복습 세션 완료: {score}/{len(questions)}", "success")
        return redirect(url_for("review.index"))

    return render_template("review/session.html", questions=questions)
