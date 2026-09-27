import json
from datetime import datetime
from CTFd.models import Challenges, db


class BingoChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "bingo"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    grid_size = db.Column(db.Integer, default=5)
    cells_json = db.Column(db.Text, default="[]")
    line_bonus = db.Column(db.Integer, default=50)
    blackout_bonus = db.Column(db.Integer, default=250)
    shuffle_cards = db.Column(db.Boolean, default=False)

    def __init__(self, *args, **kwargs):
        self.grid_size = kwargs.pop("grid_size", 5)
        self.cells_json = kwargs.pop("cells_json", "[]")
        self.line_bonus = kwargs.pop("line_bonus", 50)
        self.blackout_bonus = kwargs.pop("blackout_bonus", 250)
        self.shuffle_cards = kwargs.pop("shuffle_cards", False)
        if isinstance(self.shuffle_cards, str):
            self.shuffle_cards = self.shuffle_cards.lower() in ("true", "1", "yes", "on")
        kwargs.pop("squares_text", None)
        super(BingoChallenge, self).__init__(**kwargs)

    @property
    def cells_data(self):
        try:
            raw = json.loads(self.cells_json or "[]")
            return [
                {
                    "index": c.get("index", idx),
                    "title": c.get("title", ""),
                    "desc": c.get("desc", ""),
                    "points": c.get("points", 10),
                    "challenge_id": c.get("challenge_id"),
                }
                for idx, c in enumerate(raw)
            ]
        except Exception:
            return []


class BingoCellSolve(db.Model):
    __tablename__ = "bingo_cell_solves"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    cell_index = db.Column(db.Integer, nullable=False)
    solved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("challenge_id", "team_id", "cell_index", name="uq_bingo_team_cell"),
        db.UniqueConstraint("challenge_id", "user_id", "cell_index", name="uq_bingo_user_cell"),
    )


class BingoLineAward(db.Model):
    __tablename__ = "bingo_line_awards"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    line_id = db.Column(db.String(32), nullable=False)  # row_0, col_3, diag_main, diag_anti, blackout
    award_id = db.Column(db.Integer, db.ForeignKey("awards.id", ondelete="SET NULL"), nullable=True)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)
