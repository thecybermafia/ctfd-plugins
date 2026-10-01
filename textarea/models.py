from datetime import datetime
from CTFd.models import Challenges, db

class TextareaChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "textarea"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    min_chars = db.Column(db.Integer, default=0)
    max_chars = db.Column(db.Integer, default=5000)
    placeholder = db.Column(db.Text, default="")

    def __init__(self, *args, **kwargs):
        self.min_chars = kwargs.pop("min_chars", 0)
        self.max_chars = kwargs.pop("max_chars", 5000)
        self.placeholder = kwargs.pop("placeholder", "")
        super(TextareaChallenge, self).__init__(**kwargs)


class TextareaSubmission(db.Model):
    __tablename__ = "textarea_submissions"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    content = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(32), default="pending")  # pending, approved, rejected
    points_awarded = db.Column(db.Integer, default=0)
    feedback = db.Column(db.Text, default="")
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    challenge = db.relationship("Challenges", foreign_keys=[challenge_id])
    user = db.relationship("Users", foreign_keys=[user_id])
    team = db.relationship("Teams", foreign_keys=[team_id])
    reviewer = db.relationship("Users", foreign_keys=[reviewer_id])
