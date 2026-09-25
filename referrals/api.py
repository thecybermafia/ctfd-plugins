from flask import Blueprint, jsonify, request
from CTFd.models import Awards, Solves, Users, Teams, db
from CTFd.utils import get_config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, is_admin
from CTFd.plugins.referrals.config import ReferralConfig
from CTFd.plugins.referrals.models import ReferralCodes, Referrals
from CTFd.plugins.referrals.scoring import ReferralScoring

referrals_api = Blueprint("referrals_api", __name__, url_prefix="/api/v1/referrals")


@referrals_api.route("/me", methods=["GET"])
@authed_only
def get_my_referrals():
    user = get_current_user()
    prefix = ReferralConfig.get("referral_code_prefix", "REF-")
    code_obj = ReferralCodes.get_or_create(user.id, prefix=prefix)

    user_mode = get_config("user_mode")
    max_cap = ReferralConfig.get_int("referral_max_per_account")
    points_per_ref = ReferralConfig.get_int("referral_points")
    min_points_to_qualify = ReferralConfig.get_int("referral_min_points_to_qualify")
    min_solves_to_qualify = ReferralConfig.get_int("referral_min_solves_to_qualify")

    # Fetch recruits
    if user_mode == "teams" and user.team_id:
        recruits = Referrals.query.filter_by(referrer_team_id=user.team_id).order_by(Referrals.created_at.desc()).all()
    else:
        recruits = Referrals.query.filter_by(referrer_id=user.id).order_by(Referrals.created_at.desc()).all()

    total_recruits = len(recruits)
    qualified_count = sum(1 for r in recruits if r.status == "qualified")
    pending_count = sum(1 for r in recruits if r.status in ("pending", "flagged"))
    points_earned = sum(r.award.value for r in recruits if r.award and r.award.value)

    roster = []
    for r in recruits:
        rec_score, rec_solves = ReferralScoring.get_referee_progress(r.referee_id)
        roster.append({
            "id": r.id,
            "referee_name": r.referee.name if r.referee else "Unknown Operative",
            "status": r.status,
            "score": rec_score,
            "solves": rec_solves,
            "min_points_required": min_points_to_qualify,
            "min_solves_required": min_solves_to_qualify,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            "qualified_at": r.qualified_at.strftime("%Y-%m-%d %H:%M:%S") if r.qualified_at else None,
            "award_points": r.award.value if r.award else 0,
        })

    return jsonify({
        "success": True,
        "data": {
            "code": code_obj.code,
            "clicks": code_obj.clicks,
            "total_recruits": total_recruits,
            "qualified_count": qualified_count,
            "pending_count": pending_count,
            "points_earned": points_earned,
            "max_cap": max_cap,
            "points_per_referral": points_per_ref,
            "min_points_to_qualify": min_points_to_qualify,
            "min_solves_to_qualify": min_solves_to_qualify,
            "instructions": ReferralConfig.get("referral_instructions"),
            "roster": roster,
        }
    })
