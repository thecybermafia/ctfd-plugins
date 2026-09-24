import base64
import json
import secrets
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import requests
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from CTFd.models import Users, db
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.security.auth import login_user

sso_bp = Blueprint("sso", __name__, template_folder="templates")

PROVIDER_NAMES = {
    "disabled": "Disabled",
    "saml": "SAML",
    "discord": "Discord",
    "github": "GitHub",
    "google": "Google",
    "azure": "Azure",
    "okta": "Okta",
}

PROVIDER_ICONS = {
    "github": "fab fa-github",
    "google": "fab fa-google",
    "discord": "fab fa-discord",
    "azure": "fab fa-microsoft",
    "okta": "fas fa-shield-alt",
    "saml": "fas fa-key",
}

@sso_bp.route("/admin/sso", methods=["GET", "POST"])
@admins_only
def admin_sso():
    if request.method == "POST":
        provider = request.form.get("sso_provider", "disabled")
        user_settings = request.form.get("sso_user_settings", "all_users")
        reg_visibility = request.form.get("registration_visibility", "public")

        # Core SSO configs
        set_config("sso_provider", provider)
        set_config("sso_user_settings", user_settings)

        # Automatic sync: If All Users is set, registration visibility MUST be private
        if user_settings == "all_users":
            reg_visibility = "private"
        set_config("registration_visibility", reg_visibility)

        # Provider-specific credentials
        set_config("sso_github_client_id", request.form.get("sso_github_client_id", "").strip())
        set_config("sso_github_client_secret", request.form.get("sso_github_client_secret", "").strip())

        set_config("sso_google_client_id", request.form.get("sso_google_client_id", "").strip())
        set_config("sso_google_client_secret", request.form.get("sso_google_client_secret", "").strip())

        set_config("sso_discord_client_id", request.form.get("sso_discord_client_id", "").strip())
        set_config("sso_discord_client_secret", request.form.get("sso_discord_client_secret", "").strip())

        set_config("sso_azure_tenant_id", request.form.get("sso_azure_tenant_id", "").strip())
        set_config("sso_azure_client_id", request.form.get("sso_azure_client_id", "").strip())
        set_config("sso_azure_client_secret", request.form.get("sso_azure_client_secret", "").strip())

        set_config("sso_okta_domain", request.form.get("sso_okta_domain", "").strip())
        set_config("sso_okta_client_id", request.form.get("sso_okta_client_id", "").strip())
        set_config("sso_okta_client_secret", request.form.get("sso_okta_client_secret", "").strip())

        set_config("sso_saml_entity_id", request.form.get("sso_saml_entity_id", "").strip())
        set_config("sso_saml_sso_url", request.form.get("sso_saml_sso_url", "").strip())
        set_config("sso_saml_x509_cert", request.form.get("sso_saml_x509_cert", "").strip())

        flash("Single Sign-On settings updated successfully!", "success")
        return redirect(url_for("sso.admin_sso"))

    callback_url = request.url_root.rstrip("/") + url_for("sso.sso_callback")

    return render_template(
        "admin/sso.html",
        sso_provider=get_config("sso_provider", "disabled"),
        sso_user_settings=get_config("sso_user_settings", "all_users"),
        registration_visibility=get_config("registration_visibility", "public"),
        callback_url=callback_url,
        github_client_id=get_config("sso_github_client_id", ""),
        github_client_secret=get_config("sso_github_client_secret", ""),
        google_client_id=get_config("sso_google_client_id", ""),
        google_client_secret=get_config("sso_google_client_secret", ""),
        discord_client_id=get_config("sso_discord_client_id", ""),
        discord_client_secret=get_config("sso_discord_client_secret", ""),
        azure_tenant_id=get_config("sso_azure_tenant_id", ""),
        azure_client_id=get_config("sso_azure_client_id", ""),
        azure_client_secret=get_config("sso_azure_client_secret", ""),
        okta_domain=get_config("sso_okta_domain", ""),
        okta_client_id=get_config("sso_okta_client_id", ""),
        okta_client_secret=get_config("sso_okta_client_secret", ""),
        saml_entity_id=get_config("sso_saml_entity_id", ""),
        saml_sso_url=get_config("sso_saml_sso_url", ""),
        saml_x509_cert=get_config("sso_saml_x509_cert", ""),
    )


@sso_bp.route("/sso/login", methods=["GET"])
def sso_login():
    provider = get_config("sso_provider", "disabled")
    if not provider or provider == "disabled":
        flash("Single Sign-On is currently disabled.", "warning")
        return redirect(url_for("auth.login"))

    state = secrets.token_hex(16)
    session["sso_state"] = state
    redirect_uri = request.url_root.rstrip("/") + url_for("sso.sso_callback")

    if provider == "github":
        client_id = get_config("sso_github_client_id")
        if not client_id:
            flash("GitHub SSO is not fully configured.", "danger")
            return redirect(url_for("auth.login"))
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
        }
        return redirect(f"https://github.com/login/oauth/authorize?{urlencode(params)}")

    elif provider == "google":
        client_id = get_config("sso_google_client_id")
        if not client_id:
            flash("Google SSO is not fully configured.", "danger")
            return redirect(url_for("auth.login"))
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

    elif provider == "discord":
        client_id = get_config("sso_discord_client_id")
        if not client_id:
            flash("Discord SSO is not fully configured.", "danger")
            return redirect(url_for("auth.login"))
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify email",
            "state": state,
        }
        return redirect(f"https://discord.com/api/oauth2/authorize?{urlencode(params)}")

    elif provider == "azure":
        tenant = get_config("sso_azure_tenant_id") or "common"
        client_id = get_config("sso_azure_client_id")
        if not client_id:
            flash("Azure SSO is not fully configured.", "danger")
            return redirect(url_for("auth.login"))
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        return redirect(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}")

    elif provider == "okta":
        domain = (get_config("sso_okta_domain") or "").replace("https://", "").replace("http://", "").strip("/")
        client_id = get_config("sso_okta_client_id")
        if not domain or not client_id:
            flash("Okta SSO is not fully configured.", "danger")
            return redirect(url_for("auth.login"))
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        return redirect(f"https://{domain}/oauth2/v1/authorize?{urlencode(params)}")

    elif provider == "saml":
        sso_url = get_config("sso_saml_sso_url")
        if not sso_url:
            flash("SAML SSO is not fully configured.", "danger")
            return redirect(url_for("auth.login"))
        params = {
            "RelayState": state,
        }
        return redirect(f"{sso_url}?{urlencode(params)}")

    flash("Unsupported SSO provider.", "danger")
    return redirect(url_for("auth.login"))


@sso_bp.route("/sso/callback", methods=["GET", "POST"])
def sso_callback():
    provider = get_config("sso_provider", "disabled")
    if not provider or provider == "disabled":
        flash("Single Sign-On is disabled.", "warning")
        return redirect(url_for("auth.login"))

    # CSRF state verification
    state = request.args.get("state") or request.form.get("RelayState") or request.form.get("state")
    expected_state = session.get("sso_state")

    if not state or state != expected_state:
        flash("Invalid SSO state. Potential CSRF detected.", "danger")
        return redirect(url_for("auth.login"))

    redirect_uri = request.url_root.rstrip("/") + url_for("sso.sso_callback")
    email = None
    name = None
    oauth_uid = None

    try:
        if provider == "github":
            code = request.args.get("code")
            client_id = get_config("sso_github_client_id")
            client_secret = get_config("sso_github_client_secret")

            tok_res = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=10,
            )
            token_data = tok_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                flash(f"GitHub authentication error: {token_data.get('error_description', 'No token')}", "danger")
                return redirect(url_for("auth.login"))

            user_res = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("id"))
            name = u_data.get("login") or u_data.get("name")
            email = u_data.get("email")

            if not email:
                emails_res = requests.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"token {access_token}"},
                    timeout=10,
                )
                for e in emails_res.json():
                    if e.get("primary") and e.get("verified"):
                        email = e.get("email")
                        break

        elif provider == "google":
            code = request.args.get("code")
            client_id = get_config("sso_google_client_id")
            client_secret = get_config("sso_google_client_secret")

            tok_res = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=10,
            )
            token_data = tok_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                flash(f"Google authentication error: {token_data.get('error_description', 'No token')}", "danger")
                return redirect(url_for("auth.login"))

            user_res = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("sub"))
            email = u_data.get("email")
            name = u_data.get("name") or (email.split("@")[0] if email else None)

        elif provider == "discord":
            code = request.args.get("code")
            client_id = get_config("sso_discord_client_id")
            client_secret = get_config("sso_discord_client_secret")

            tok_res = requests.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            token_data = tok_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                flash(f"Discord authentication error: {token_data.get('error_description', 'No token')}", "danger")
                return redirect(url_for("auth.login"))

            user_res = requests.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("id"))
            email = u_data.get("email")
            name = u_data.get("username")

        elif provider == "azure":
            code = request.args.get("code")
            tenant = get_config("sso_azure_tenant_id") or "common"
            client_id = get_config("sso_azure_client_id")
            client_secret = get_config("sso_azure_client_secret")

            tok_res = requests.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=10,
            )
            token_data = tok_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                flash(f"Azure authentication error: {token_data.get('error_description', 'No token')}", "danger")
                return redirect(url_for("auth.login"))

            user_res = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("id"))
            email = u_data.get("mail") or u_data.get("userPrincipalName")
            name = u_data.get("displayName") or (email.split("@")[0] if email else None)

        elif provider == "okta":
            code = request.args.get("code")
            domain = (get_config("sso_okta_domain") or "").replace("https://", "").replace("http://", "").strip("/")
            client_id = get_config("sso_okta_client_id")
            client_secret = get_config("sso_okta_client_secret")

            tok_res = requests.post(
                f"https://{domain}/oauth2/v1/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=10,
            )
            token_data = tok_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                flash(f"Okta authentication error: {token_data.get('error_description', 'No token')}", "danger")
                return redirect(url_for("auth.login"))

            user_res = requests.get(
                f"https://{domain}/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("sub"))
            email = u_data.get("email")
            name = u_data.get("name") or u_data.get("preferred_username")

        elif provider == "saml":
            saml_response = request.form.get("SAMLResponse") or request.args.get("SAMLResponse")
            if not saml_response:
                flash("Missing SAML response payload.", "danger")
                return redirect(url_for("auth.login"))

            xml_data = base64.b64decode(saml_response)
            root = ET.fromstring(xml_data)
            # Basic SAML NameID / attribute extraction
            name_id = None
            for elem in root.iter():
                if "NameID" in elem.tag:
                    name_id = elem.text
                    break
            if name_id:
                email = name_id if "@" in name_id else f"{name_id}@saml.local"
                name = name_id.split("@")[0]
                oauth_uid = name_id

    except Exception as e:
        flash(f"SSO authentication exception: {str(e)}", "danger")
        return redirect(url_for("auth.login"))

    if not email:
        flash("Could not obtain verified email address from SSO provider.", "danger")
        return redirect(url_for("auth.login"))

    if not name:
        name = email.split("@")[0]

    # Find or provision CTFd user
    user = Users.query.filter((Users.email == email) | (Users.name == name)).first()
    if not user:
        # Check if name is taken
        base_name = name
        counter = 1
        while Users.query.filter_by(name=name).first():
            name = f"{base_name}_{counter}"
            counter += 1

        user = Users(
            name=name,
            email=email,
            password=secrets.token_urlsafe(32),
            type="user",
            verified=True,
        )
        db.session.add(user)
        db.session.commit()

    # Mark user verified and log in
    user.verified = True
    db.session.commit()
    login_user(user)

    flash(f"Successfully authenticated via {PROVIDER_NAMES.get(provider, provider.upper())}!", "success")
    return redirect(url_for("challenges.listing"))
