from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.crossword.challenge import CrosswordChallengeType
from CTFd.plugins.crossword.models import CrosswordChallenge

def load(app):
    with app.app_context():
        CrosswordChallenge.__table__.create(bind=db.engine, checkfirst=True)

        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            existing = {c["name"] for c in inspector.get_columns("crossword_challenge")}
            with db.engine.connect() as conn:
                if "partial_scoring" not in existing:
                    conn.execute(text("ALTER TABLE crossword_challenge ADD COLUMN partial_scoring TINYINT(1) DEFAULT 0"))
                if "points_per_word" not in existing:
                    conn.execute(text("ALTER TABLE crossword_challenge ADD COLUMN points_per_word INT DEFAULT 10"))
                try:
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass

    CHALLENGE_CLASSES["crossword"] = CrosswordChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/crossword/assets/"
    )
