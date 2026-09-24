from flask import flash, redirect, request, url_for
from CTFd.models import Users
from CTFd.plugins import register_admin_plugin_menu_bar
from CTFd.plugins.sso.routes import PROVIDER_NAMES, sso_bp
from CTFd.utils import get_config

def load(app):
    app.register_blueprint(sso_bp)
    register_admin_plugin_menu_bar(title="Single Sign-On", route="/admin/sso")

    @app.before_request
    def enforce_sso_policy():
        # Intercept standard username/password login when SSO is mandatory
        if request.path == "/login" and request.method == "POST":
            # Allow emergency admin bypass with specific query param if needed
            if request.args.get("emergency_auth") == "true":
                return

            provider = get_config("sso_provider", "disabled")
            if provider and provider != "disabled":
                user_settings = get_config("sso_user_settings", "all_users")
                prov_name = PROVIDER_NAMES.get(provider, provider.upper())

                if user_settings == "all_users":
                    flash(
                        f"Single Sign-On is required for all users. Please authenticate using {prov_name}.",
                        "danger",
                    )
                    return redirect(url_for("auth.login"))

                elif user_settings == "admins_only":
                    name = request.form.get("name")
                    if name:
                        user = Users.query.filter(
                            (Users.name == name) | (Users.email == name)
                        ).first()
                        if user and user.type == "admin":
                            flash(
                                f"Single Sign-On is required for Administrator accounts. Please authenticate using {prov_name}.",
                                "danger",
                            )
                            return redirect(url_for("auth.login"))
