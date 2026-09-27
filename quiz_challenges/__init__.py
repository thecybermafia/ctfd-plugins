from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.quiz_challenges.challenge import QuizChallengeType
from CTFd.plugins.quiz_challenges.models import QuizChallenge


def load(app):
    with app.app_context():
        QuizChallenge.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["quiz"] = QuizChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/quiz_challenges/assets/"
    )
