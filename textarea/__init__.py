from CTFd.models import db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
)
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.textarea.api import textarea_bp
from CTFd.plugins.textarea.challenge import TextareaChallengeType
from CTFd.plugins.textarea.models import TextareaChallenge, TextareaSubmission

def load(app):
    with app.app_context():
        TextareaChallenge.__table__.create(bind=db.engine, checkfirst=True)
        TextareaSubmission.__table__.create(bind=db.engine, checkfirst=True)

        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            existing = {c["name"] for c in inspector.get_columns("textarea_challenge")}
            with db.engine.connect() as conn:
                if "auto_grade" not in existing:
                    conn.execute(text("ALTER TABLE textarea_challenge ADD COLUMN auto_grade TINYINT(1) DEFAULT 0"))
                if "required_keywords" not in existing:
                    conn.execute(text("ALTER TABLE textarea_challenge ADD COLUMN required_keywords TEXT NULL"))
                if "auto_pass_mode" not in existing:
                    conn.execute(text("ALTER TABLE textarea_challenge ADD COLUMN auto_pass_mode VARCHAR(32) DEFAULT 'all'"))
                if "auto_award_points" not in existing:
                    conn.execute(text("ALTER TABLE textarea_challenge ADD COLUMN auto_award_points INT DEFAULT 0"))
                try:
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass

    app.register_blueprint(textarea_bp)
    CHALLENGE_CLASSES["textarea"] = TextareaChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/textarea/assets/"
    )

    register_admin_plugin_menu_bar(title="Manual Verification", route="/admin/textarea_submissions")
