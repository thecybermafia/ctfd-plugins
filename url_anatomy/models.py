import json
from CTFd.models import Challenges, db


class UrlAnatomyChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "url_anatomy"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    urls_json = db.Column(db.Text, default="[]")
    enable_qr_code = db.Column(db.Boolean, default=False)
    allow_punycode_toggle = db.Column(db.Boolean, default=True)
    explanation = db.Column(db.Text, default="")

    def __init__(self, *args, **kwargs):
        self.urls_json = kwargs.pop("urls_json", "[]")
        self.enable_qr_code = kwargs.pop("enable_qr_code", False)
        if isinstance(self.enable_qr_code, str):
            self.enable_qr_code = self.enable_qr_code.lower() in ("true", "1", "yes", "on")
        self.allow_punycode_toggle = kwargs.pop("allow_punycode_toggle", True)
        if isinstance(self.allow_punycode_toggle, str):
            self.allow_punycode_toggle = self.allow_punycode_toggle.lower() in ("true", "1", "yes", "on")
        self.explanation = kwargs.pop("explanation", "")
        super(UrlAnatomyChallenge, self).__init__(**kwargs)

    @property
    def urls_data(self):
        try:
            return json.loads(self.urls_json or "[]")
        except Exception:
            return []
