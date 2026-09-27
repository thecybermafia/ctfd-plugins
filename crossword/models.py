import json
from datetime import datetime
from CTFd.models import Challenges, db


class CrosswordChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "crossword"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    grid_width = db.Column(db.Integer, default=10)
    grid_height = db.Column(db.Integer, default=10)
    clues_json = db.Column(db.Text, default="[]")
    solution_hash = db.Column(db.String(128), default="")
    solution_word = db.Column(db.String(128), default="")
    partial_scoring = db.Column(db.Boolean, default=False)
    points_per_word = db.Column(db.Integer, default=10)

    def __init__(self, *args, **kwargs):
        self.grid_width = kwargs.pop("grid_width", 10)
        self.grid_height = kwargs.pop("grid_height", 10)
        self.clues_json = kwargs.pop("clues_json", "[]")
        self.solution_hash = kwargs.pop("solution_hash", "")
        self.solution_word = kwargs.pop("solution_word", "")
        self.partial_scoring = kwargs.pop("partial_scoring", False)
        if isinstance(self.partial_scoring, str):
            self.partial_scoring = self.partial_scoring.lower() in ("true", "1", "yes", "on")
        self.points_per_word = int(kwargs.pop("points_per_word", 10) or 10)
        kwargs.pop("clues_text", None)
        super(CrosswordChallenge, self).__init__(**kwargs)

    @property
    def clues_data(self):
        try:
            raw = json.loads(self.clues_json or "[]")
            return [
                {
                    "number": c.get("number", idx + 1),
                    "clue": c.get("clue", ""),
                    "length": c.get("length", len(c.get("answer", ""))),
                }
                for idx, c in enumerate(raw)
            ]
        except Exception:
            return []


class CrosswordWordSolve(db.Model):
    __tablename__ = "crossword_word_solves"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    clue_number = db.Column(db.Integer, nullable=False)
    word = db.Column(db.String(64), nullable=False)
    solved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("challenge_id", "user_id", "clue_number", name="uq_crossword_user_word"),
    )
