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

    app.register_blueprint(textarea_bp)
    CHALLENGE_CLASSES["textarea"] = TextareaChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/textarea/assets/"
    )

    register_admin_plugin_menu_bar(title="Textarea Reviews", route="/admin/textarea_submissions")
