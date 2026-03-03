from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Attempt, AttemptAnswer, Question, WrongAnswer

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
    wrong_items = (
        WrongAnswer.query.filter_by(user_id=current_user.id, mastered=False)
        .order_by(WrongAnswer.wrong_count.desc(), WrongAnswer.last_wrong_at.desc())
        .all()
    )
    return render_template("review/index.html", wrong_items=wrong_items)


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

        attempt = Attempt(user_id=current_user.id, quiz_id=questions[0].quiz_id, is_review=True, total=len(questions), score=0)
        db.session.add(attempt)
        db.session.flush()

        score = 0
        for q in questions:
            ua = request.form.get(f"q_{q.id}", "")
            ok = _is_correct(q, ua)
            db.session.add(AttemptAnswer(attempt_id=attempt.id, question_id=q.id, user_answer=ua, is_correct=ok))

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
