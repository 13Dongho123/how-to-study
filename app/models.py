from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    exams = db.relationship("Exam", back_populates="user", cascade="all, delete-orphan")
    plans = db.relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    documents = db.relationship("Document", back_populates="user", cascade="all, delete-orphan")
    quizzes = db.relationship("Quiz", back_populates="user", cascade="all, delete-orphan")
    attempts = db.relationship("Attempt", back_populates="user", cascade="all, delete-orphan")
    wrong_answers = db.relationship("WrongAnswer", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    exam_date = db.Column(db.Date, nullable=False, index=True)
    daily_minutes = db.Column(db.Integer, nullable=False)
    weekend_minutes = db.Column(db.Integer, nullable=False)
    excluded_weekdays = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="exams")
    study_plans = db.relationship("StudyPlan", back_populates="exam", cascade="all, delete-orphan")


class Topic(db.Model):
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    weight = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, nullable=True)


class StudyPlan(db.Model):
    __tablename__ = "study_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False, index=True)
    plan_date = db.Column(db.Date, nullable=False, index=True)
    week_no = db.Column(db.Integer, nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=True)
    minutes = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="plans")
    exam = db.relationship("Exam", back_populates="study_plans")
    topic = db.relationship("Topic")

    __table_args__ = (
        db.Index("ix_study_plans_user_date", "user_id", "plan_date"),
    )


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=True)
    stored_filename = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    source_url = db.Column(db.String(500), nullable=True)
    text_extracted = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="documents")
    quizzes = db.relationship("Quiz", back_populates="document")


class SyllabusTopic(db.Model):
    __tablename__ = "syllabus_topics"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    keywords = db.relationship(
        "SyllabusKeyword", back_populates="topic", cascade="all, delete-orphan"
    )


class SyllabusKeyword(db.Model):
    __tablename__ = "syllabus_keywords"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(
        db.Integer, db.ForeignKey("syllabus_topics.id"), nullable=False, index=True
    )
    keyword = db.Column(db.String(100), nullable=False, index=True)

    topic = db.relationship("SyllabusTopic", back_populates="keywords")

    __table_args__ = (
        db.UniqueConstraint("topic_id", "keyword", name="uq_topic_keyword"),
    )


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)
    source_type = db.Column(db.String(20), nullable=False, index=True)  # TEXT | PDF
    scope_mode = db.Column(db.String(20), nullable=False, index=True)  # ALL | SYLLABUS | CUSTOM
    focus_keywords = db.Column(db.JSON, nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True, index=True)
    source_excerpt = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="quizzes")
    document = db.relationship("Document", back_populates="quizzes")
    questions = db.relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = db.relationship("Attempt", back_populates="quiz", cascade="all, delete-orphan")


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)  # mcq | short
    question_text = db.Column(db.Text, nullable=False)
    choices = db.Column(db.JSON, nullable=True)
    answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, nullable=True)

    quiz = db.relationship("Quiz", back_populates="questions")
    attempt_answers = db.relationship(
        "AttemptAnswer", back_populates="question", cascade="all, delete-orphan"
    )
    wrong_answers = db.relationship("WrongAnswer", back_populates="question")


class Attempt(db.Model):
    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False, index=True)
    is_review = db.Column(db.Boolean, nullable=False, default=False, index=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="attempts")
    quiz = db.relationship("Quiz", back_populates="attempts")
    answers = db.relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")


class AttemptAnswer(db.Model):
    __tablename__ = "attempt_answers"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(
        db.Integer, db.ForeignKey("attempts.id"), nullable=False, index=True
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id"), nullable=False, index=True
    )
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)

    attempt = db.relationship("Attempt", back_populates="answers")
    question = db.relationship("Question", back_populates="attempt_answers")


class WrongAnswer(db.Model):
    __tablename__ = "wrong_answers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id"), nullable=False, index=True
    )
    wrong_count = db.Column(db.Integer, nullable=False, default=1, index=True)
    last_wrong_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    mastered = db.Column(db.Boolean, nullable=False, default=False, index=True)

    user = db.relationship("User", back_populates="wrong_answers")
    question = db.relationship("Question", back_populates="wrong_answers")

    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id", name="uq_user_question_wrong"),
        db.Index(
            "ix_wrong_answers_user_sort", "user_id", "mastered", "wrong_count", "last_wrong_at"
        ),
    )
