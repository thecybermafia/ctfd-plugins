from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.crossword.challenge import CrosswordChallengeType
from CTFd.plugins.crossword.models import CrosswordChallenge

def load(app):
    with app.app_context():
        CrosswordChallenge.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["crossword"] = CrosswordChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/crossword/assets/"
    )
