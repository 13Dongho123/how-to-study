from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not email or not password:
            flash("이메일과 비밀번호를 입력하세요.", "danger")
            return render_template("auth/register.html")
        if password != confirm:
            flash("비밀번호 확인이 일치하지 않습니다.", "danger")
            return render_template("auth/register.html")
        if User.query.filter_by(email=email).first():
            flash("이미 사용 중인 이메일입니다.", "warning")
            return render_template("auth/register.html")

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("회원가입 완료. 로그인하세요.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("로그인되었습니다.", "success")
            return redirect(url_for("main.dashboard"))

        flash("로그인 실패: 이메일 또는 비밀번호를 확인하세요.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("auth.login"))
