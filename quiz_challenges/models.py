import json
from CTFd.models import Challenges, db


class QuizChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "quiz"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    question_mode = db.Column(db.String(32), default="single")  # single | multiple
    options_json = db.Column(db.Text, default="[]")
    randomize_options = db.Column(db.Boolean, default=True)
    max_attempts = db.Column(db.Integer, default=0)  # 0 for unlimited
    penalty_per_attempt = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text, default="")
    partial_scoring = db.Column(db.Boolean, default=False)

    def __init__(self, *args, **kwargs):
        self.question_mode = kwargs.pop("question_mode", "single")
        self.options_json = kwargs.pop("options_json", "[]")
        self.randomize_options = kwargs.pop("randomize_options", True)
        if isinstance(self.randomize_options, str):
            self.randomize_options = self.randomize_options.lower() in ("true", "1", "yes")
        self.max_attempts = int(kwargs.pop("max_attempts", 0) or 0)
        self.penalty_per_attempt = int(kwargs.pop("penalty_per_attempt", 0) or 0)
        self.explanation = kwargs.pop("explanation", "")
        self.partial_scoring = kwargs.pop("partial_scoring", False)
        if isinstance(self.partial_scoring, str):
            self.partial_scoring = self.partial_scoring.lower() in ("true", "1", "yes")
        kwargs.pop("options_text", None)
        super(QuizChallenge, self).__init__(**kwargs)

    @property
    def options_data(self):
        try:
            return json.loads(self.options_json or "[]")
        except Exception:
            return []

    def get_sanitized_options(self):
        """Returns options list for players without the 'correct' flag."""
        opts = self.options_data
        sanitized = []
        for opt in opts:
            sanitized.append({
                "id": opt.get("id"),
                "text": opt.get("text", "")
            })
        return sanitized
