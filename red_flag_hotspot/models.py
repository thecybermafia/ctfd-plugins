import json
from CTFd.models import Challenges, db


class HotspotChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "red_flag_hotspot"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    image_url = db.Column(db.String(512), nullable=False, default="")
    hotspots_json = db.Column(db.Text, default="[]")
    max_clicks = db.Column(db.Integer, default=5)
    tolerance_radius = db.Column(db.Float, default=6.0)
    min_hits_required = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text, default="")

    def __init__(self, *args, **kwargs):
        self.image_url = kwargs.pop("image_url", "")
        self.hotspots_json = kwargs.pop("hotspots_json", "[]")
        self.max_clicks = int(kwargs.pop("max_clicks", 5) or 5)
        self.tolerance_radius = float(kwargs.pop("tolerance_radius", 6.0) or 6.0)
        self.min_hits_required = int(kwargs.pop("min_hits_required", 0) or 0)
        self.explanation = kwargs.pop("explanation", "")
        super(HotspotChallenge, self).__init__(**kwargs)

    @property
    def hotspots_data(self):
        try:
            return json.loads(self.hotspots_json or "[]")
        except Exception:
            return []
