import os
import uuid
from datetime import datetime

import requests
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    Attempt,
    AttemptAnswer,
    Document,
    Question,
    Quiz,
    SyllabusKeyword,
    SyllabusTopic,
    WrongAnswer,
)
from app.services.ai import AIService
from app.services.content import (
    allowed_file,
    build_safe_upload_path,
    extract_relevant_passages,
    extract_text_from_pdf,
    shrink_text,
)

quiz_bp = Blueprint("quiz", __name__)


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


@quiz_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_quiz():
    syllabus_topics = SyllabusTopic.query.order_by(SyllabusTopic.name.asc()).all()

    if request.method == "POST":
        source_type = request.form.get("source_type", "TEXT")
        scope_mode = request.form.get("scope_mode", "ALL")
        custom_keywords_raw = request.form.get("custom_keywords", "")
        num_questions = request.form.get("num_questions", type=int) or 10
        source_text = ""
        document = None

        try:
            if source_type == "TEXT":
                source_text = request.form.get("source_text", "").strip()
            elif source_type == "PDF":
                file = request.files.get("pdf_file")
                if not file or not file.filename:
                    raise ValueError("PDF 파일을 선택하세요.")
                if not allowed_file(file.filename):
                    raise ValueError("PDF 파일만 업로드 가능합니다.")

                original_filename = file.filename
                safe_name, base_path = build_safe_upload_path(
                    current_app.config["UPLOAD_FOLDER"], original_filename
                )
                uniq_name = f"{uuid.uuid4().hex}_{safe_name}"
                file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], uniq_name)
                file.save(file_path)

                extracted = extract_text_from_pdf(file_path)
                document = Document(
                    user_id=current_user.id,
                    original_filename=original_filename,
                    stored_filename=uniq_name,
                    file_path=file_path,
                    text_extracted=extracted,
                )
                db.session.add(document)
                db.session.flush()
                source_text = extracted
            elif source_type == "URL":
                target_url = request.form.get("source_url", "").strip()
                if not target_url:
                    raise ValueError("URL을 입력하세요.")
                resp = requests.get(target_url, timeout=8)
                resp.raise_for_status()
                source_text = resp.text[:30000]
                document = Document(
                    user_id=current_user.id,
                    source_url=target_url,
                    text_extracted=source_text,
                )
                db.session.add(document)
                db.session.flush()
            else:
                raise ValueError("알 수 없는 입력 소스입니다.")

            if not source_text.strip():
                raise ValueError("퀴즈 생성에 사용할 텍스트가 비어 있습니다.")

            focus_keywords = []
            if scope_mode == "SYLLABUS":
                keyword_ids = [int(kid) for kid in request.form.getlist("keyword_ids") if kid.isdigit()]
                if keyword_ids:
                    kws = SyllabusKeyword.query.filter(SyllabusKeyword.id.in_(keyword_ids)).all()
                    focus_keywords = [k.keyword for k in kws]
                else:
                    topic_id = request.form.get("syllabus_topic_id", type=int)
                    if topic_id:
                        kws = SyllabusKeyword.query.filter_by(topic_id=topic_id).all()
                        focus_keywords = [k.keyword for k in kws]
                if not focus_keywords:
                    raise ValueError("SYLLABUS 모드에서는 최소 1개 키워드를 선택하세요.")
            elif scope_mode == "CUSTOM":
                focus_keywords = [x.strip() for x in custom_keywords_raw.split(",") if x.strip()]
                if not focus_keywords:
                    raise ValueError("CUSTOM 모드에서는 키워드를 입력하세요.")

            if scope_mode in {"SYLLABUS", "CUSTOM"}:
                ai_context, matched = extract_relevant_passages(
                    source_text,
                    focus_keywords,
                    window=2,
                    max_chars=12000,
                )
                if not matched:
                    flash("키워드 문맥이 적어 fallback 모드(키워드 중심 생성)로 진행합니다.", "warning")
            else:
                ai_context = shrink_text(source_text, max_chars=16000)

            ai_service = AIService(current_app.config.get("OPENAI_API_KEY"))
            questions_payload = ai_service.generate_quiz(
                source_text=ai_context,
                num_questions=min(max(num_questions, 1), 20),
                scope_mode=scope_mode,
                focus_keywords=focus_keywords,
            )
            if not questions_payload:
                raise ValueError("유효한 문제를 생성하지 못했습니다.")

            quiz = Quiz(
                user_id=current_user.id,
                title=request.form.get("title", "") or f"퀴즈 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                source_type=source_type,
                scope_mode=scope_mode,
                focus_keywords=focus_keywords,
                document_id=document.id if document else None,
                source_excerpt=ai_context[:2000],
            )
            db.session.add(quiz)
            db.session.flush()

            for q in questions_payload:
                question = Question(
                    quiz_id=quiz.id,
                    type=q.get("type", "short"),
                    question_text=q.get("question", ""),
                    choices=q.get("choices") if q.get("type") == "mcq" else None,
                    answer=q.get("answer", ""),
                    explanation=q.get("explanation", ""),
                    tags=q.get("tags", []),
                )
                db.session.add(question)

            db.session.commit()
            flash("퀴즈 생성 완료", "success")
            return redirect(url_for("quiz.solve_quiz", id=quiz.id))

        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f"퀴즈 생성 실패: {exc}", "danger")

    return render_template("quiz/new.html", syllabus_topics=syllabus_topics)


@quiz_bp.route("/<int:id>", methods=["GET", "POST"])
@login_required
def solve_quiz(id):
    quiz = Quiz.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    questions = quiz.questions

    if request.method == "POST":
        attempt = Attempt(user_id=current_user.id, quiz_id=quiz.id, is_review=False, score=0, total=len(questions))
        db.session.add(attempt)
        db.session.flush()

        correct_count = 0
        for q in questions:
            ua = request.form.get(f"q_{q.id}", "")
            ok = _is_correct(q, ua)
            if ok:
                correct_count += 1

            db.session.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    question_id=q.id,
                    user_answer=ua,
                    is_correct=ok,
                )
            )

            if not ok:
                wrong = WrongAnswer.query.filter_by(user_id=current_user.id, question_id=q.id).first()
                if wrong:
                    wrong.wrong_count += 1
                    wrong.last_wrong_at = datetime.utcnow()
                    wrong.mastered = False
                else:
                    db.session.add(
                        WrongAnswer(
                            user_id=current_user.id,
                            question_id=q.id,
                            wrong_count=1,
                            last_wrong_at=datetime.utcnow(),
                            mastered=False,
                        )
                    )

        attempt.score = correct_count
        db.session.commit()

        flash(f"채점 완료: {correct_count}/{len(questions)}", "info")
        return redirect(url_for("quiz.solve_quiz", id=quiz.id))

    return render_template("quiz/solve.html", quiz=quiz, questions=questions)
