import datetime
from flask import request, session
from CTFd.models import Users, Teams, db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
    register_user_page_menu_bar,
)
from CTFd.utils.user import authed, get_current_user, get_ip
from CTFd.plugins.referrals.anti_cheat import AntiCheatEngine, resolve_user_ip
from CTFd.plugins.referrals.api import referrals_api
from CTFd.plugins.referrals.config import ReferralConfig
from CTFd.plugins.referrals.listener import register_referral_listeners
from CTFd.plugins.referrals.models import ReferralCodes, Referrals
from CTFd.plugins.referrals.routes import referrals_bp
from CTFd.plugins.referrals.scoring import ReferralScoring


def load(app):
    with app.app_context():
        ReferralCodes.__table__.create(bind=db.engine, checkfirst=True)
        Referrals.__table__.create(bind=db.engine, checkfirst=True)

    app.register_blueprint(referrals_bp)
    app.register_blueprint(referrals_api)

    def get_user_referral_info(user_id):
        user = Users.query.filter_by(id=user_id).first()
        if not user:
            return None
        code_obj = ReferralCodes.query.filter_by(user_id=user_id).first()
        recruits = Referrals.query.filter_by(referrer_id=user_id).order_by(Referrals.created_at.desc()).all()
        for r in recruits:
            r.live_score, r.live_solves = ReferralScoring.get_referee_progress(r.referee_id)
        my_ref = Referrals.query.filter_by(referee_id=user_id).first()
        is_disabled = ReferralConfig.is_user_disabled(user_id)
        points_earned = sum(r.award.value for r in recruits if r.award and r.award.value)
        return {
            "code": code_obj.code if code_obj else None,
            "clicks": code_obj.clicks if code_obj else 0,
            "recruits": recruits,
            "total_recruits": len(recruits),
            "qualified_count": sum(1 for r in recruits if r.status == "qualified"),
            "pending_count": sum(1 for r in recruits if r.status in ("pending", "flagged")),
            "points_earned": points_earned,
            "my_referral": my_ref,
            "is_disabled": is_disabled,
            "configs": ReferralConfig.get_all(),
        }

    def get_team_referral_info(team_id):
        team = Teams.query.filter_by(id=team_id).first()
        captain_code_obj = None
        captain_name = None
        if team and team.captain_id:
            captain = Users.query.filter_by(id=team.captain_id).first()
            if captain:
                captain_name = captain.name
                captain_code_obj = ReferralCodes.query.filter_by(user_id=captain.id).first()

        recruits = Referrals.query.filter_by(referrer_team_id=team_id).order_by(Referrals.created_at.desc()).all()
        for r in recruits:
            r.live_score, r.live_solves = ReferralScoring.get_referee_progress(r.referee_id)
        is_disabled = ReferralConfig.is_team_disabled(team_id)
        points_earned = sum(r.award.value for r in recruits if r.award and r.award.value)

        my_ref = None
        if team:
            if team.id:
                my_ref = Referrals.query.filter_by(referee_team_id=team.id).first()
            if not my_ref and team.captain_id:
                my_ref = Referrals.query.filter_by(referee_id=team.captain_id).first()
            if not my_ref and team.members:
                member_ids = [m.id for m in team.members]
                my_ref = Referrals.query.filter(Referrals.referee_id.in_(member_ids)).first()
            if my_ref and not my_ref.referee_team_id:
                try:
                    my_ref.referee_team_id = team.id
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        return {
            "captain_code": captain_code_obj.code if captain_code_obj else None,
            "captain_name": captain_name,
            "captain_id": team.captain_id if team else None,
            "clicks": captain_code_obj.clicks if captain_code_obj else 0,
            "recruits": recruits,
            "total_recruits": len(recruits),
            "qualified_count": sum(1 for r in recruits if r.status == "qualified"),
            "pending_count": sum(1 for r in recruits if r.status in ("pending", "flagged")),
            "points_earned": points_earned,
            "my_referral": my_ref,
            "is_disabled": is_disabled,
            "configs": ReferralConfig.get_all(),
        }

    app.jinja_env.globals["get_user_referral_info"] = get_user_referral_info
    app.jinja_env.globals["get_team_referral_info"] = get_team_referral_info

    register_plugin_assets_directory(app, base_path="/plugins/referrals/assets/")

    # By default, do NOT display in the navbar unless explicitly enabled in admin panel
    if ReferralConfig.get_bool("referral_show_in_navbar"):
        register_user_page_menu_bar(title="Referrals", route="/referrals")

    register_admin_plugin_menu_bar(title="Referrals", route="/admin/referrals")

    register_referral_listeners()

    @app.before_request
    def intercept_referral_tracking():
        # 1. Capture ?ref=... parameter from incoming invite links
        ref_param = request.args.get("ref")
        if ref_param:
            code_str = str(ref_param).strip().upper()
            session["referral_code"] = code_str

        # 2. Defensive SSO/OAuth Onboarding Linker
        # If user is authenticated, has a referral code in session or cookie, and account was created within the last 5 minutes
        if authed():
            code = session.get("referral_code") or request.cookies.get("ctfd_referral")
            if code:
                user = get_current_user()
                if user and user.created:
                    age_seconds = (datetime.datetime.utcnow() - user.created).total_seconds()
                    # Only link if the account was created very recently (onboarding window)
                    if age_seconds <= 300:
                        existing = Referrals.query.filter_by(referee_id=user.id).first()
                        if not existing:
                            code_str = str(code).strip().upper()
                            code_obj = ReferralCodes.query.filter_by(code=code_str).first()
                            if code_obj:
                                referrer_user = Users.query.filter_by(id=code_obj.user_id).first()
                                if referrer_user:
                                    current_ip = get_ip()
                                    referrer_ip = resolve_user_ip(referrer_user.id)
                                    valid, status, msg, notes = AntiCheatEngine.evaluate_new_referral(
                                        referrer_user=referrer_user,
                                        referee_user=user,
                                        code_obj=code_obj,
                                        referee_ip=current_ip,
                                    )
                                    if valid:
                                        new_ref = Referrals(
                                            referrer_id=referrer_user.id,
                                            referee_id=user.id,
                                            referrer_team_id=referrer_user.team_id,
                                            referee_team_id=user.team_id,
                                            code_used=code_str,
                                            status=status,
                                            referrer_ip=referrer_ip,
                                            referee_ip=current_ip,
                                            notes=notes,
                                        )
                                        db.session.add(new_ref)
                                        db.session.commit()
                # Clear session code once evaluated
                session.pop("referral_code", None)

    @app.after_request
    def persist_referral_cookie(response):
        ref_param = request.args.get("ref")
        if ref_param:
            code_str = str(ref_param).strip().upper()
            ttl_days = ReferralConfig.get_int("referral_cookie_ttl_days")
            response.set_cookie(
                "ctfd_referral",
                code_str,
                max_age=86400 * max(1, ttl_days),
                httponly=True,
                samesite="Lax",
                path="/",
            )
        return response
