import datetime
from flask import request, session
from CTFd.models import Users, db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
    register_user_page_menu_bar,
)
from CTFd.utils.user import authed, get_current_user, get_ip
from CTFd.plugins.referrals.anti_cheat import AntiCheatEngine
from CTFd.plugins.referrals.api import referrals_api
from CTFd.plugins.referrals.config import ReferralConfig
from CTFd.plugins.referrals.listener import register_referral_listeners
from CTFd.plugins.referrals.models import ReferralCodes, Referrals
from CTFd.plugins.referrals.routes import referrals_bp


def load(app):
    with app.app_context():
        ReferralCodes.__table__.create(bind=db.engine, checkfirst=True)
        Referrals.__table__.create(bind=db.engine, checkfirst=True)

    app.register_blueprint(referrals_bp)
    app.register_blueprint(referrals_api)

    register_plugin_assets_directory(app, base_path="/plugins/referrals/assets/")
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
                                            referrer_ip=getattr(referrer_user, "ip", None),
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
