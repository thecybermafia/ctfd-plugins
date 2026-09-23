import json
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

    def __init__(self, *args, **kwargs):
        self.grid_width = kwargs.pop("grid_width", 10)
        self.grid_height = kwargs.pop("grid_height", 10)
        self.clues_json = kwargs.pop("clues_json", "[]")
        self.solution_hash = kwargs.pop("solution_hash", "")
        self.solution_word = kwargs.pop("solution_word", "")
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
