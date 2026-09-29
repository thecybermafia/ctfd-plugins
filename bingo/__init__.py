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

        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            existing = {c["name"] for c in inspector.get_columns("bingo_challenge")}
            with db.engine.connect() as conn:
                if "shuffle_cards" not in existing:
                    conn.execute(text("ALTER TABLE bingo_challenge ADD COLUMN shuffle_cards TINYINT(1) DEFAULT 0"))
                    try:
                        conn.commit()
                    except Exception:
                        pass
        except Exception:
            pass

    app.register_blueprint(bingo_bp)
    CHALLENGE_CLASSES["bingo"] = BingoChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/bingo/assets/"
    )
