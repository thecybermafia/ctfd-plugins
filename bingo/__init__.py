from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.bingo.api import bingo_bp
from CTFd.plugins.bingo.challenge import BingoChallengeType
from CTFd.plugins.bingo.models import BingoCellSolve, BingoChallenge, BingoLineAward

def load(app):
    with app.app_context():
        BingoChallenge.__table__.create(bind=db.engine, checkfirst=True)
        BingoCellSolve.__table__.create(bind=db.engine, checkfirst=True)
        BingoLineAward.__table__.create(bind=db.engine, checkfirst=True)

    app.register_blueprint(bingo_bp)
    CHALLENGE_CLASSES["bingo"] = BingoChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/bingo/assets/"
    )
