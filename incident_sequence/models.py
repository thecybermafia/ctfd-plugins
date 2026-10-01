import json
from CTFd.models import Challenges, db


class IncidentSequenceChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "incident_sequence"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    steps_json = db.Column(db.Text, default="[]")
    distractors_json = db.Column(db.Text, default="[]")
    allow_distractor_bin = db.Column(db.Boolean, default=True)
    explanation = db.Column(db.Text, default="")

    def __init__(self, *args, **kwargs):
        self.steps_json = kwargs.pop("steps_json", "[]")
        self.distractors_json = kwargs.pop("distractors_json", "[]")
        self.allow_distractor_bin = kwargs.pop("allow_distractor_bin", True)
        if isinstance(self.allow_distractor_bin, str):
            self.allow_distractor_bin = self.allow_distractor_bin.lower() in ("true", "1", "yes", "on", "checked")
        self.explanation = kwargs.pop("explanation", "")
        super(IncidentSequenceChallenge, self).__init__(**kwargs)

    @db.validates("allow_distractor_bin")
    def validate_allow_distractor_bin(self, key, value):
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on", "checked")
        return bool(value)

    @property
    def steps_data(self):
        try:
            return json.loads(self.steps_json or "[]")
        except Exception:
            return []

    @property
    def distractors_data(self):
        try:
            return json.loads(self.distractors_json or "[]")
        except Exception:
            return []

    def get_shuffled_cards(self):
        import random
        cards = []
        for s in self.steps_data:
            cards.append({
                "id": str(s.get("id")),
                "text": s.get("text") or s.get("title") or s.get("description", "")
            })
        for d in self.distractors_data:
            cards.append({
                "id": str(d.get("id")),
                "text": d.get("text") or d.get("title") or d.get("description", "")
            })
        rnd = random.Random(self.id or 42)
        rnd.shuffle(cards)
        return cards
