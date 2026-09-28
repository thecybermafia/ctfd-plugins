import json
from CTFd.models import Challenges, db


class PhishingInboxChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "phishing_inbox"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    emails_json = db.Column(db.Text, default="[]")
    action_options = db.Column(db.String(128), default="report,safe,delete")
    min_accuracy_percent = db.Column(db.Integer, default=100)
    show_auth_headers = db.Column(db.Boolean, default=True)
    max_attempts = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text, default="")

    def __init__(self, *args, **kwargs):
        self.emails_json = kwargs.pop("emails_json", "[]")
        self.action_options = kwargs.pop("action_options", "report,safe,delete")
        self.min_accuracy_percent = int(kwargs.pop("min_accuracy_percent", 100) or 100)
        self.show_auth_headers = kwargs.pop("show_auth_headers", True)
        if isinstance(self.show_auth_headers, str):
            self.show_auth_headers = self.show_auth_headers.lower() in ("true", "1", "yes", "on")
        self.max_attempts = int(kwargs.pop("max_attempts", 0) or 0)
        self.explanation = kwargs.pop("explanation", "")
        kwargs.pop("emails_text", None)
        super(PhishingInboxChallenge, self).__init__(**kwargs)

    @property
    def emails_data(self):
        try:
            return json.loads(self.emails_json or "[]")
        except Exception:
            return []
