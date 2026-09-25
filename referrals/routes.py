from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from CTFd.models import Awards, Solves, Users, Teams, db
from CTFd.utils import get_config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, get_ip
from CTFd.plugins.referrals.anti_cheat import resolve_user_ip
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
            # Check if recruiter is disabled
            if not ReferralConfig.is_user_disabled(code_obj.user_id):
                user = Users.query.filter_by(id=code_obj.user_id).first()
                if not (user and user.team_id and ReferralConfig.is_team_disabled(user.team_id)):
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

    is_disabled = ReferralConfig.is_user_disabled(user.id) or (
        user.team_id and ReferralConfig.is_team_disabled(user.team_id)
    )

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
        is_disabled=is_disabled,
        configs=ReferralConfig.get_all(),
    )


@referrals_bp.route("/api/v1/referrals/me", methods=["GET"])
@authed_only
def api_referrals_me():
    user = get_current_user()
    prefix = ReferralConfig.get("referral_code_prefix", "REF-")
    code_obj = ReferralCodes.get_or_create(user.id, prefix=prefix)

    user_mode = get_config("user_mode")
    max_cap = ReferralConfig.get_int("referral_max_per_account")
    points_per_ref = ReferralConfig.get_int("referral_points")
    min_points_to_qualify = ReferralConfig.get_int("referral_min_points_to_qualify")
    min_solves_to_qualify = ReferralConfig.get_int("referral_min_solves_to_qualify")

    is_disabled = ReferralConfig.is_user_disabled(user.id) or (
        user.team_id and ReferralConfig.is_team_disabled(user.team_id)
    )

    if user_mode == "teams" and user.team_id:
        recruits = Referrals.query.filter_by(referrer_team_id=user.team_id).order_by(Referrals.created_at.desc()).all()
    else:
        recruits = Referrals.query.filter_by(referrer_id=user.id).order_by(Referrals.created_at.desc()).all()

    total_recruits = len(recruits)
    qualified_count = sum(1 for r in recruits if r.status == "qualified")
    pending_count = sum(1 for r in recruits if r.status in ("pending", "flagged"))
    points_earned = sum(r.award.value for r in recruits if r.award and r.award.value)

    recruits_data = []
    for r in recruits:
        score, solves = ReferralScoring.get_referee_progress(r.referee_id)
        recruits_data.append({
            "id": r.id,
            "referee_name": r.referee.name if r.referee else "Unknown",
            "team_name": r.referee.team.name if (r.referee and r.referee.team) else None,
            "created_at": r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else None,
            "live_score": score,
            "live_solves": solves,
            "status": r.status,
            "bonus": r.award.value if r.award else 0,
        })

    my_ref = Referrals.query.filter_by(referee_id=user.id).first()
    my_ref_data = None
    if my_ref:
        my_ref_data = {
            "referrer_name": my_ref.referrer.name if my_ref.referrer else "Operative",
            "code_used": my_ref.code_used,
        }

    return jsonify({
        "success": True,
        "data": {
            "code": code_obj.code,
            "url": f"{request.url_root}referrals/join?ref={code_obj.code}",
            "clicks": code_obj.clicks or 0,
            "points_earned": points_earned,
            "total_recruits": total_recruits,
            "pending_count": pending_count,
            "qualified_count": qualified_count,
            "max_cap": max_cap,
            "points_per_ref": points_per_ref,
            "min_points_to_qualify": min_points_to_qualify,
            "min_solves_to_qualify": min_solves_to_qualify,
            "is_disabled": is_disabled,
            "my_referral": my_ref_data,
            "recruits": recruits_data,
            "program_name": ReferralConfig.get("referral_program_name", "Referral & Recruitment Directive"),
            "instructions": ReferralConfig.get("referral_instructions", ""),
        }
    })


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
        # Attempt to dynamically resolve referrer IP if stored as Unknown
        if not r.referrer_ip:
            r.referrer_ip = resolve_user_ip(r.referrer_id)
        r.is_same_ip = (r.referrer_ip and r.referee_ip and r.referrer_ip.strip() == r.referee_ip.strip())

    disabled_user_ids = ReferralConfig.get_disabled_user_ids()
    disabled_team_ids = ReferralConfig.get_disabled_team_ids()

    disabled_users = Users.query.filter(Users.id.in_(disabled_user_ids)).all() if disabled_user_ids else []
    disabled_teams = Teams.query.filter(Teams.id.in_(disabled_team_ids)).all() if disabled_team_ids else []

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
        disabled_users=disabled_users,
        disabled_teams=disabled_teams,
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

    if action == "approve_flagged" and referral_id:
        success, msg = ReferralScoring.approve_flagged_referral(referral_id)
        flash(msg, "success" if success else "warning")

    elif action == "revoke" and referral_id:
        success, msg = ReferralScoring.revoke_referral(referral_id, reason="Revoked via Admin Control Panel")
        flash(msg, "info")

    elif action == "delete" and referral_id:
        ref = Referrals.query.filter_by(id=referral_id).first()
        if ref:
            ReferralScoring.revoke_referral(ref.id, reason="Deleted")
            db.session.delete(ref)
            db.session.commit()
            flash("Referral record permanently deleted.", "success")

    elif action == "disable_user":
        user_id = request.form.get("user_id")
        if user_id:
            ReferralConfig.add_disabled_user(user_id)
            user = Users.query.filter_by(id=user_id).first()
            flash(f"Referral privileges suspended for user {user.name if user else user_id}.", "warning")

    elif action == "enable_user":
        user_id = request.form.get("user_id")
        if user_id:
            ReferralConfig.remove_disabled_user(user_id)
            user = Users.query.filter_by(id=user_id).first()
            flash(f"Referral privileges re-enabled for user {user.name if user else user_id}.", "success")

    elif action == "disable_team":
        team_id = request.form.get("team_id")
        if team_id:
            ReferralConfig.add_disabled_team(team_id)
            team = Teams.query.filter_by(id=team_id).first()
            flash(f"Referral privileges suspended for team {team.name if team else team_id}.", "warning")

    elif action == "enable_team":
        team_id = request.form.get("team_id")
        if team_id:
            ReferralConfig.remove_disabled_team(team_id)
            team = Teams.query.filter_by(id=team_id).first()
            flash(f"Referral privileges re-enabled for team {team.name if team else team_id}.", "success")

    elif action == "add_exclusion":
        target_type = request.form.get("target_type")
        identifier = request.form.get("identifier", "").strip()
        if identifier:
            if target_type == "user":
                target_user = Users.query.filter(
                    (Users.id == identifier) if identifier.isdigit() else (Users.name == identifier)
                ).first()
                if target_user:
                    ReferralConfig.add_disabled_user(target_user.id)
                    flash(f"Added user '{target_user.name}' to referral exclusion list.", "warning")
                else:
                    flash(f"User '{identifier}' not found.", "danger")
            elif target_type == "team":
                target_team = Teams.query.filter(
                    (Teams.id == identifier) if identifier.isdigit() else (Teams.name == identifier)
                ).first()
                if target_team:
                    ReferralConfig.add_disabled_team(target_team.id)
                    flash(f"Added team '{target_team.name}' to referral exclusion list.", "warning")
                else:
                    flash(f"Team '{identifier}' not found.", "danger")

    tab = request.form.get("tab") or ("exclusions" if "disable" in (action or "") or "enable" in (action or "") or "exclusion" in (action or "") else "audit")
    return redirect(url_for("referrals.admin_referrals", tab=tab))
