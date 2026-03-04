import os
import click
from flask import Flask
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from app.extensions import db, login_manager, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app import models  # noqa: F401
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.exam import exam_bp
    from app.blueprints.quiz import quiz_bp
    from app.blueprints.review import review_bp
    from app.blueprints.stats import stats_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(exam_bp, url_prefix="/exam")
    app.register_blueprint(quiz_bp, url_prefix="/quiz")
    app.register_blueprint(review_bp, url_prefix="/review")
    app.register_blueprint(stats_bp, url_prefix="/stats")

    @app.cli.command("seed")
    def seed_command():
        from app.seed import seed_defaults

        seed_defaults()
        click.echo("Seed completed.")

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        return "업로드 파일이 너무 큽니다. 최대 10MB까지 허용됩니다.", 413

    return app
