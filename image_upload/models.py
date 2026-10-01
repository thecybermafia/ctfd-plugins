from datetime import datetime
from CTFd.models import Challenges, Files, db

class ImageUploadFiles(Files):
    __mapper_args__ = {"polymorphic_identity": "image_upload"}

class ImageUploadChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "image_upload"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    max_file_size_mb = db.Column(db.Integer, default=10)
    allowed_extensions = db.Column(db.String(128), default="png,jpg,jpeg,webp,gif")

    def __init__(self, *args, **kwargs):
        super(ImageUploadChallenge, self).__init__(**kwargs)
        self.max_file_size_mb = kwargs.get("max_file_size_mb", 10)
        self.allowed_extensions = kwargs.get("allowed_extensions", "png,jpg,jpeg,webp,gif")


class ImageUploadSubmission(db.Model):
    __tablename__ = "image_upload_submissions"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(32), default="pending")  # pending, approved, rejected
    points_awarded = db.Column(db.Integer, default=0)
    feedback = db.Column(db.Text, default="")
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    challenge = db.relationship("Challenges", foreign_keys=[challenge_id])
    user = db.relationship("Users", foreign_keys=[user_id])
    team = db.relationship("Teams", foreign_keys=[team_id])
    file = db.relationship("Files", foreign_keys=[file_id])
    reviewer = db.relationship("Users", foreign_keys=[reviewer_id])
