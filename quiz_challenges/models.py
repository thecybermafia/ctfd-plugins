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
            raw = json.loads(self.options_json or "[]")
            if isinstance(raw, dict):
                raw = list(raw.values())
            if not isinstance(raw, list):
                raw = [str(self.options_json)]

            normalized = []
            for idx, item in enumerate(raw):
                if isinstance(item, dict):
                    opt_id = str(item.get("id") or f"opt_{idx}")
                    opt_text = str(item.get("text", "")).strip()
                    is_correct = bool(item.get("correct", False))
                    normalized.append({
                        "id": opt_id,
                        "text": opt_text,
                        "correct": is_correct
                    })
                elif isinstance(item, (str, int, float, bool)):
                    clean = str(item).strip()
                    is_correct = clean.startswith("*") or clean.lower().startswith("[x]")
                    if clean.startswith("*"):
                        clean = clean.lstrip("*").strip()
                    elif clean.lower().startswith("[x]"):
                        clean = clean[3:].strip()
                    elif clean.startswith("[ ]"):
                        clean = clean[3:].strip()
                    normalized.append({
                        "id": f"opt_{idx}",
                        "text": clean,
                        "correct": is_correct
                    })
            return normalized
        except Exception:
            return []

    @property
    def options_text(self):
        try:
            opts = self.options_data
            lines = []
            for o in opts:
                prefix = "* " if o.get("correct") else ""
                lines.append(f"{prefix}{o.get('text', '')}")
            return "\n".join(lines)
        except Exception:
            return ""

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
