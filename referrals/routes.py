from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from CTFd.models import Awards, Solves, Users, Teams, db
from CTFd.utils import get_config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, get_ip
from CTFd.plugins.referrals.config import ReferralConfig
from CTFd.plugins.referrals.models import ReferralCodes, Referrals
from CTFd.plugins.referrals.scoring import ReferralScoring

referrals_bp = Blueprint(
    "referrals",
    __name__,
    template_folder="templates",
    static_folder="assets",
    static_url_path="/plugins/referrals/assets",
)


@referrals_bp.route("/referrals/join", methods=["GET"])
def join_via_referral():
    code = request.args.get("ref", "").strip().upper()
    if code:
        code_obj = ReferralCodes.query.filter_by(code=code).first()
        if code_obj:
            code_obj.clicks = (code_obj.clicks or 0) + 1
            db.session.commit()
            session["referral_code"] = code

    # Redirect to registration or login
    target_url = url_for("auth.register")
    resp = redirect(target_url)
    if code:
        ttl_days = ReferralConfig.get_int("referral_cookie_ttl_days")
        resp.set_cookie(
            "ctfd_referral",
            code,
            max_age=86400 * max(1, ttl_days),
            httponly=True,
            samesite="Lax",
            path="/",
        )
    return resp


@referrals_bp.route("/referrals", methods=["GET"])
@authed_only
def referrals_dashboard():
    user = get_current_user()
    prefix = ReferralConfig.get("referral_code_prefix", "REF-")
    code_obj = ReferralCodes.get_or_create(user.id, prefix=prefix)

    user_mode = get_config("user_mode")
    max_cap = ReferralConfig.get_int("referral_max_per_account")
    points_per_ref = ReferralConfig.get_int("referral_points")
    min_points_to_qualify = ReferralConfig.get_int("referral_min_points_to_qualify")
    min_solves_to_qualify = ReferralConfig.get_int("referral_min_solves_to_qualify")

    # Fetch recruits for current user (or user's team)
    if user_mode == "teams" and user.team_id:
        recruits = Referrals.query.filter_by(referrer_team_id=user.team_id).order_by(Referrals.created_at.desc()).all()
    else:
        recruits = Referrals.query.filter_by(referrer_id=user.id).order_by(Referrals.created_at.desc()).all()

    total_recruits = len(recruits)
    qualified_count = sum(1 for r in recruits if r.status == "qualified")
    pending_count = sum(1 for r in recruits if r.status in ("pending", "flagged"))
    points_earned = sum(r.award.value for r in recruits if r.award and r.award.value)

    # Attach live score & solves progress to each recruit record
    for r in recruits:
        r.live_score, r.live_solves = ReferralScoring.get_referee_progress(r.referee_id)

    # Check if current user was recruited by someone
    my_referral = Referrals.query.filter_by(referee_id=user.id).first()

    return render_template(
        "referrals.html",
        user=user,
        code_obj=code_obj,
        recruits=recruits,
        total_recruits=total_recruits,
        qualified_count=qualified_count,
        pending_count=pending_count,
        points_earned=points_earned,
        max_cap=max_cap,
        points_per_ref=points_per_ref,
        min_points_to_qualify=min_points_to_qualify,
        min_solves_to_qualify=min_solves_to_qualify,
        my_referral=my_referral,
        configs=ReferralConfig.get_all(),
    )


@referrals_bp.route("/admin/referrals", methods=["GET"])
@admins_only
def admin_referrals():
    configs = ReferralConfig.get_all()
    referrals_list = Referrals.query.order_by(Referrals.created_at.desc()).all()

    # Pre-calculate progress and metrics
    total_codes = ReferralCodes.query.count()
    total_recruits = len(referrals_list)
    total_qualified = sum(1 for r in referrals_list if r.status == "qualified")
    total_flagged = sum(1 for r in referrals_list if r.status == "flagged")
    total_pending = sum(1 for r in referrals_list if r.status == "pending")

    cat = ReferralConfig.get("referral_award_category", "Recruitment Directive")
    total_points_minted = db.session.query(db.func.sum(Awards.value)).filter_by(category=cat).scalar() or 0

    for r in referrals_list:
        r.live_score, r.live_solves = ReferralScoring.get_referee_progress(r.referee_id)
        r.is_same_ip = (r.referrer_ip and r.referee_ip and r.referrer_ip.strip() == r.referee_ip.strip())

    return render_template(
        "admin/referrals.html",
        configs=configs,
        referrals=referrals_list,
        total_codes=total_codes,
        total_recruits=total_recruits,
        total_qualified=total_qualified,
        total_flagged=total_flagged,
        total_pending=total_pending,
        total_points_minted=total_points_minted,
        active_tab=request.args.get("tab", "audit"),
    )


@referrals_bp.route("/admin/referrals/settings", methods=["POST"])
@admins_only
def admin_save_settings():
    form_data = request.form.to_dict()
    ReferralConfig.update_all(form_data)
    flash("Referral system configuration saved successfully.", "success")
    return redirect(url_for("referrals.admin_referrals", tab=request.args.get("tab", "settings")))


@referrals_bp.route("/admin/referrals/actions", methods=["POST"])
@admins_only
def admin_referral_actions():
    action = request.form.get("action")
    referral_id = request.form.get("referral_id")

    if not referral_id:
        flash("Invalid referral target.", "danger")
        return redirect(url_for("referrals.admin_referrals"))

    ref = Referrals.query.filter_by(id=referral_id).first()
    if not ref:
        flash("Referral entry not found.", "danger")
        return redirect(url_for("referrals.admin_referrals"))

    if action == "approve_flagged":
        success, msg = ReferralScoring.approve_flagged_referral(ref.id)
        flash(msg, "success" if success else "warning")

    elif action == "revoke":
        success, msg = ReferralScoring.revoke_referral(ref.id, reason="Revoked via Admin Control Panel")
        flash(msg, "info")

    elif action == "delete":
        # If awards were attached, clean them up first
        ReferralScoring.revoke_referral(ref.id, reason="Deleted")
        db.session.delete(ref)
        db.session.commit()
        flash("Referral record permanently deleted.", "success")

    return redirect(url_for("referrals.admin_referrals", tab="audit"))
