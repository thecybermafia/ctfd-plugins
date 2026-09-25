import datetime
import hashlib
import random
import string
from CTFd.models import db


class ReferralCodes(db.Model):
    __tablename__ = "referral_codes"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    code = db.Column(db.String(32), unique=True, index=True, nullable=False)
    clicks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("Users", foreign_keys="ReferralCodes.user_id", lazy="select")

    @classmethod
    def get_or_create(cls, user_id, prefix="REF-"):
        code_obj = cls.query.filter_by(user_id=user_id).first()
        if not code_obj:
            from CTFd.models import Users
            user = Users.query.filter_by(id=user_id).first()
            user_part = "".join(c for c in (user.name if user else "OP") if c.isalnum()).upper()[:6]
            if not user_part:
                user_part = "OP"
            
            # Generate random 5-char alphanumeric suffix
            chars = string.ascii_uppercase + string.digits
            for _ in range(10):
                rand_suffix = "".join(random.choices(chars, k=5))
                candidate = f"{prefix}{user_part}-{rand_suffix}"
                if not cls.query.filter_by(code=candidate).first():
                    code_obj = cls(user_id=user_id, code=candidate)
                    db.session.add(code_obj)
                    db.session.commit()
                    break
        return code_obj


class Referrals(db.Model):
    __tablename__ = "referrals"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referee_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    referrer_team_id = db.Column(
        db.Integer,
        db.ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referee_team_id = db.Column(
        db.Integer,
        db.ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    code_used = db.Column(db.String(32), nullable=False)

    # Status: 'pending', 'qualified', 'flagged', 'cap_reached', 'rejected', 'revoked'
    status = db.Column(db.String(32), default="pending", index=True, nullable=False)

    referrer_ip = db.Column(db.String(45), nullable=True)
    referee_ip = db.Column(db.String(45), nullable=True)

    award_id = db.Column(
        db.Integer,
        db.ForeignKey("awards.id", ondelete="SET NULL"),
        nullable=True,
    )
    referee_award_id = db.Column(
        db.Integer,
        db.ForeignKey("awards.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    qualified_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    referrer = db.relationship("Users", foreign_keys="Referrals.referrer_id", lazy="select")
    referee = db.relationship("Users", foreign_keys="Referrals.referee_id", lazy="select")
    referrer_team = db.relationship("Teams", foreign_keys="Referrals.referrer_team_id", lazy="select")
    referee_team = db.relationship("Teams", foreign_keys="Referrals.referee_team_id", lazy="select")
    award = db.relationship("Awards", foreign_keys="Referrals.award_id", lazy="select")
    referee_award = db.relationship("Awards", foreign_keys="Referrals.referee_award_id", lazy="select")
