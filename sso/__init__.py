from flask import flash, redirect, request, url_for
from CTFd.plugins import register_admin_plugin_menu_bar
from CTFd.plugins.sso.routes import PROVIDER_NAMES, sso_bp
from CTFd.utils import get_config
from CTFd.utils.user import authed, is_admin

def load(app):
    app.register_blueprint(sso_bp)
    register_admin_plugin_menu_bar(title="Single Sign-On", route="/admin/sso")

    @app.before_request
    def enforce_sso_policy():
        provider = get_config("sso_provider", "disabled")
        if not provider or provider == "disabled":
            return

        # 1. When browsing directly to /admin, unauthenticated users can still log in with local accounts
        if request.path in ("/admin", "/admin/"):
            if not is_admin():
                return redirect(url_for("auth.login", fallback=1, next="/admin"))

        # 2. When browsing or submitting to /login
        if request.path == "/login":
            # If already authenticated, let standard CTFd handle redirect
            if authed():
                return

            is_fallback = (
                request.args.get("fallback") == "1"
                or request.form.get("fallback") == "1"
                or request.args.get("emergency_auth") == "true"
                or request.args.get("next", "").startswith("/admin")
            )

            # GET requests: browsing directly to /login without fallback=1 redirects to SSO provider
            if request.method == "GET":
                if is_fallback:
                    return  # Render local login form
                return redirect(url_for("sso.sso_login"))

            # POST requests: local credential login is allowed via fallback mode
            if request.method == "POST":
                if is_fallback:
                    return  # Allow CTFd auth.login to verify username & password
                
                # Direct POST to /login without fallback while SSO is enabled
                prov_name = PROVIDER_NAMES.get(provider, provider.upper())
                flash(
                    f"Single Sign-On is enabled ({prov_name}). Users with local CTFd accounts may still log in using the fallback URL (/login?fallback=1).",
                    "warning",
                )
                return redirect(url_for("auth.login", fallback=1))
