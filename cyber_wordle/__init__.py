from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.cyber_wordle.challenge import WordleChallengeType
from CTFd.plugins.cyber_wordle.models import WordleChallenge, WordleGuess


def load(app):
    with app.app_context():
        WordleChallenge.__table__.create(bind=db.engine, checkfirst=True)
        WordleGuess.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["wordle"] = WordleChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/cyber_wordle/assets/"
    )
