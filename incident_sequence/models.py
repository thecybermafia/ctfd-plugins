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
            self.allow_distractor_bin = self.allow_distractor_bin.lower() in ("true", "1", "yes", "on")
        self.explanation = kwargs.pop("explanation", "")
        super(IncidentSequenceChallenge, self).__init__(**kwargs)

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
