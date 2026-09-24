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
    "disabled": "Disable SSO",
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
    host_root = request.url_root.rstrip("/")

    # Compute default Service Provider URLs
    default_saml_sp_url = f"{host_root}/sso/saml/metadata"
    default_saml_login_url = f"{host_root}/sso/saml/login"
    default_sp_xml = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{default_saml_sp_url}">
  <md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="false" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{default_saml_login_url}" index="1"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""

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

        # ----------------------------------------------------
        # SAML Configuration
        # ----------------------------------------------------
        set_config("sso_saml_idp_metadata_url", request.form.get("sso_saml_idp_metadata_url", "").strip())
        set_config("sso_saml_idp_metadata_xml", request.form.get("sso_saml_idp_metadata_xml", "").strip())
        set_config("sso_saml_sp_url", request.form.get("sso_saml_sp_url", "").strip() or default_saml_sp_url)
        set_config("sso_saml_sp_login_url", request.form.get("sso_saml_sp_login_url", "").strip() or default_saml_login_url)
        set_config("sso_saml_sp_metadata_xml", request.form.get("sso_saml_sp_metadata_xml", "").strip() or default_sp_xml)

        # ----------------------------------------------------
        # Discord OAuth Configuration
        # ----------------------------------------------------
        set_config("sso_discord_client_id", request.form.get("sso_discord_client_id", "").strip())
        set_config("sso_discord_client_secret", request.form.get("sso_discord_client_secret", "").strip())
        set_config("sso_discord_scope", request.form.get("sso_discord_scope", "").strip() or "identify email")

        # ----------------------------------------------------
        # GitHub OAuth Configuration
        # ----------------------------------------------------
        set_config("sso_github_client_id", request.form.get("sso_github_client_id", "").strip())
        set_config("sso_github_client_secret", request.form.get("sso_github_client_secret", "").strip())
        set_config("sso_github_scope", request.form.get("sso_github_scope", "").strip() or "user:email")
        set_config("sso_github_base_url", request.form.get("sso_github_base_url", "").strip())
        set_config("sso_github_auth_url", request.form.get("sso_github_auth_url", "").strip())
        set_config("sso_github_token_url", request.form.get("sso_github_token_url", "").strip())

        # ----------------------------------------------------
        # Google OAuth Configuration
        # ----------------------------------------------------
        set_config("sso_google_client_id", request.form.get("sso_google_client_id", "").strip())
        set_config("sso_google_client_secret", request.form.get("sso_google_client_secret", "").strip())
        set_config("sso_google_scope", request.form.get("sso_google_scope", "").strip() or "openid email profile")
        set_config("sso_google_hosted_domain", request.form.get("sso_google_hosted_domain", "").strip())

        # ----------------------------------------------------
        # Azure OAuth Configuration
        # ----------------------------------------------------
        set_config("sso_azure_client_id", request.form.get("sso_azure_client_id", "").strip())
        set_config("sso_azure_client_secret", request.form.get("sso_azure_client_secret", "").strip())
        set_config("sso_azure_tenant", request.form.get("sso_azure_tenant", "").strip() or "common")
        set_config("sso_azure_scope", request.form.get("sso_azure_scope", "").strip() or "openid email profile")

        # ----------------------------------------------------
        # Okta OAuth Configuration
        # ----------------------------------------------------
        set_config("sso_okta_client_id", request.form.get("sso_okta_client_id", "").strip())
        set_config("sso_okta_client_secret", request.form.get("sso_okta_client_secret", "").strip())
        set_config("sso_okta_base_url", request.form.get("sso_okta_base_url", "").strip())
        set_config("sso_okta_scope", request.form.get("sso_okta_scope", "").strip() or "openid email profile")
        set_config("sso_okta_auth_url", request.form.get("sso_okta_auth_url", "").strip())
        set_config("sso_okta_token_url", request.form.get("sso_okta_token_url", "").strip())

        flash("Single Sign-On configuration updated successfully!", "success")
        return redirect(url_for("sso.admin_sso"))

    # Compute provider-specific callback URLs matching CTFd documentation
    callbacks = {
        "discord": f"{host_root}/oauth/discord/authorized",
        "github": f"{host_root}/oauth/github/authorized",
        "google": f"{host_root}/oauth/google/authorized",
        "azure": f"{host_root}/oauth/azure/authorized",
        "okta": f"{host_root}/oauth/okta/authorized",
        "general": f"{host_root}/oauth/authorized",
    }

    return render_template(
        "admin/sso.html",
        sso_provider=get_config("sso_provider", "disabled"),
        sso_user_settings=get_config("sso_user_settings", "all_users"),
        registration_visibility=get_config("registration_visibility", "public"),
        callbacks=callbacks,
        # SAML
        saml_idp_metadata_url=get_config("sso_saml_idp_metadata_url", ""),
        saml_idp_metadata_xml=get_config("sso_saml_idp_metadata_xml", ""),
        saml_sp_url=get_config("sso_saml_sp_url", default_saml_sp_url),
        saml_sp_login_url=get_config("sso_saml_sp_login_url", default_saml_login_url),
        saml_sp_metadata_xml=get_config("sso_saml_sp_metadata_xml", default_sp_xml),
        # Discord
        discord_client_id=get_config("sso_discord_client_id", ""),
        discord_client_secret=get_config("sso_discord_client_secret", ""),
        discord_scope=get_config("sso_discord_scope", "identify email"),
        # GitHub
        github_client_id=get_config("sso_github_client_id", ""),
        github_client_secret=get_config("sso_github_client_secret", ""),
        github_scope=get_config("sso_github_scope", "user:email"),
        github_base_url=get_config("sso_github_base_url", ""),
        github_auth_url=get_config("sso_github_auth_url", ""),
        github_token_url=get_config("sso_github_token_url", ""),
        # Google
        google_client_id=get_config("sso_google_client_id", ""),
        google_client_secret=get_config("sso_google_client_secret", ""),
        google_scope=get_config("sso_google_scope", "openid email profile"),
        google_hosted_domain=get_config("sso_google_hosted_domain", ""),
        # Azure
        azure_client_id=get_config("sso_azure_client_id", ""),
        azure_client_secret=get_config("sso_azure_client_secret", ""),
        azure_tenant=get_config("sso_azure_tenant", "common"),
        azure_scope=get_config("sso_azure_scope", "openid email profile"),
        # Okta
        okta_client_id=get_config("sso_okta_client_id", ""),
        okta_client_secret=get_config("sso_okta_client_secret", ""),
        okta_base_url=get_config("sso_okta_base_url", ""),
        okta_scope=get_config("sso_okta_scope", "openid email profile"),
        okta_auth_url=get_config("sso_okta_auth_url", ""),
        okta_token_url=get_config("sso_okta_token_url", ""),
    )


@sso_bp.route("/sso/login", methods=["GET"])
def sso_login():
    provider = get_config("sso_provider", "disabled")
    if not provider or provider == "disabled":
        flash("Single Sign-On is currently disabled.", "warning")
        return redirect(url_for("auth.login", fallback=1))

    state = secrets.token_hex(16)
    session["sso_state"] = state
    redirect_uri = request.url_root.rstrip("/") + f"/oauth/{provider}/authorized"

    if provider == "github":
        client_id = get_config("sso_github_client_id")
        if not client_id:
            flash("GitHub SSO is not configured. Please enter Client ID and Secret in Admin > Single Sign-On.", "danger")
            return redirect(url_for("auth.login", fallback=1))
        
        auth_endpoint = get_config("sso_github_auth_url") or "https://github.com/login/oauth/authorize"
        scope = get_config("sso_github_scope") or "user:email"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        return redirect(f"{auth_endpoint}?{urlencode(params)}")

    elif provider == "google":
        client_id = get_config("sso_google_client_id")
        if not client_id:
            flash("Google SSO is not configured. Please enter Client ID and Secret in Admin > Single Sign-On.", "danger")
            return redirect(url_for("auth.login", fallback=1))
        
        scope = get_config("sso_google_scope") or "openid email profile"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
        }
        hd = get_config("sso_google_hosted_domain")
        if hd:
            params["hd"] = hd
        return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

    elif provider == "discord":
        client_id = get_config("sso_discord_client_id")
        if not client_id:
            flash("Discord SSO is not configured. Please enter Client ID and Secret in Admin > Single Sign-On.", "danger")
            return redirect(url_for("auth.login", fallback=1))
        
        scope = get_config("sso_discord_scope") or "identify email"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
        }
        return redirect(f"https://discord.com/api/oauth2/authorize?{urlencode(params)}")

    elif provider == "azure":
        tenant = get_config("sso_azure_tenant") or "common"
        client_id = get_config("sso_azure_client_id")
        if not client_id:
            flash("Azure SSO is not configured. Please enter Client ID and Secret in Admin > Single Sign-On.", "danger")
            return redirect(url_for("auth.login", fallback=1))
        
        scope = get_config("sso_azure_scope") or "openid email profile"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
        }
        return redirect(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}")

    elif provider == "okta":
        base_url = (get_config("sso_okta_base_url") or "").rstrip("/")
        client_id = get_config("sso_okta_client_id")
        if not base_url or not client_id:
            flash("Okta SSO is not configured. Please enter Base URL and Client ID in Admin > Single Sign-On.", "danger")
            return redirect(url_for("auth.login", fallback=1))
        
        auth_endpoint = get_config("sso_okta_auth_url") or f"{base_url}/oauth2/default/v1/authorize"
        scope = get_config("sso_okta_scope") or "openid email profile"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
        }
        return redirect(f"{auth_endpoint}?{urlencode(params)}")

    elif provider == "saml":
        idp_url = get_config("sso_saml_idp_metadata_url")
        if not idp_url:
            flash("SAML SSO is not fully configured.", "danger")
            return redirect(url_for("auth.login", fallback=1))
        params = {
            "RelayState": state,
        }
        return redirect(f"{idp_url}?{urlencode(params)}")

    flash("Unsupported SSO provider.", "danger")
    return redirect(url_for("auth.login", fallback=1))


@sso_bp.route("/oauth/<provider>/authorized", methods=["GET", "POST"])
@sso_bp.route("/sso/<provider>/callback", methods=["GET", "POST"])
@sso_bp.route("/sso/callback", methods=["GET", "POST"])
def sso_callback(provider=None):
    if not provider:
        provider = get_config("sso_provider", "disabled")
        
    if not provider or provider == "disabled":
        flash("Single Sign-On is disabled.", "warning")
        return redirect(url_for("auth.login", fallback=1))

    # CSRF state verification
    state = request.args.get("state") or request.form.get("RelayState") or request.form.get("state")
    expected_state = session.get("sso_state")

    if not state or state != expected_state:
        flash("Invalid SSO state. Potential CSRF detected.", "danger")
        return redirect(url_for("auth.login", fallback=1))

    redirect_uri = request.url_root.rstrip("/") + f"/oauth/{provider}/authorized"
    email = None
    name = None
    oauth_uid = None

    try:
        if provider == "github":
            code = request.args.get("code")
            client_id = get_config("sso_github_client_id")
            client_secret = get_config("sso_github_client_secret")
            token_endpoint = get_config("sso_github_token_url") or "https://github.com/login/oauth/access_token"

            tok_res = requests.post(
                token_endpoint,
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
                flash(f"GitHub authentication error: {token_data.get('error_description', 'No token received')}", "danger")
                return redirect(url_for("auth.login", fallback=1))

            base_api = get_config("sso_github_base_url") or "https://api.github.com"
            base_api = base_api.rstrip("/")
            user_res = requests.get(
                f"{base_api}/user",
                headers={"Authorization": f"token {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("id"))
            name = u_data.get("login") or u_data.get("name")
            email = u_data.get("email")

            if not email:
                emails_res = requests.get(
                    f"{base_api}/user/emails",
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
                flash(f"Google authentication error: {token_data.get('error_description', 'No token received')}", "danger")
                return redirect(url_for("auth.login", fallback=1))

            user_res = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("sub"))
            email = u_data.get("email")
            name = u_data.get("name") or (email.split("@")[0] if email else None)

            # Enforce hosted domain restriction if configured
            required_hd = get_config("sso_google_hosted_domain")
            if required_hd and email:
                user_domain = email.split("@")[-1].lower()
                if user_domain != required_hd.lower():
                    flash(f"Authentication rejected: Account must belong to @{required_hd}", "danger")
                    return redirect(url_for("auth.login", fallback=1))

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
                flash(f"Discord authentication error: {token_data.get('error_description', 'No token received')}", "danger")
                return redirect(url_for("auth.login", fallback=1))

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
            tenant = get_config("sso_azure_tenant") or "common"
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
                flash(f"Azure authentication error: {token_data.get('error_description', 'No token received')}", "danger")
                return redirect(url_for("auth.login", fallback=1))

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
            base_url = (get_config("sso_okta_base_url") or "").rstrip("/")
            client_id = get_config("sso_okta_client_id")
            client_secret = get_config("sso_okta_client_secret")
            token_endpoint = get_config("sso_okta_token_url") or f"{base_url}/oauth2/default/v1/token"

            tok_res = requests.post(
                token_endpoint,
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
                flash(f"Okta authentication error: {token_data.get('error_description', 'No token received')}", "danger")
                return redirect(url_for("auth.login", fallback=1))

            userinfo_endpoint = f"{base_url}/oauth2/default/v1/userinfo"
            user_res = requests.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            u_data = user_res.json()
            oauth_uid = str(u_data.get("sub"))
            email = u_data.get("email")
            name = u_data.get("name") or u_data.get("preferred_username") or (email.split("@")[0] if email else None)

        elif provider == "saml":
            saml_response = request.form.get("SAMLResponse")
            if not saml_response:
                flash("Missing SAMLResponse payload.", "danger")
                return redirect(url_for("auth.login", fallback=1))

            xml_data = base64.b64decode(saml_response)
            root = ET.fromstring(xml_data)
            ns = {
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            }
            name_id = root.find(".//saml:NameID", ns)
            if name_id is not None and name_id.text:
                email = name_id.text.strip()
                name = email.split("@")[0]
                oauth_uid = email
            else:
                flash("Could not parse NameID from SAML response assertion.", "danger")
                return redirect(url_for("auth.login", fallback=1))

    except Exception as e:
        flash(f"Authentication processing error: {str(e)}", "danger")
        return redirect(url_for("auth.login", fallback=1))

    if not email:
        flash("Could not retrieve a verified email address from identity provider.", "danger")
        return redirect(url_for("auth.login", fallback=1))

    # Match or auto-provision user
    user = Users.query.filter_by(email=email).first()
    if not user:
        candidate_name = name or email.split("@")[0]
        base_name = candidate_name
        counter = 1
        while Users.query.filter_by(name=candidate_name).first():
            candidate_name = f"{base_name}_{counter}"
            counter += 1

        user = Users(
            name=candidate_name,
            email=email,
            oauth_id=oauth_uid,
            verified=True,
        )
        db.session.add(user)
        db.session.commit()
    else:
        if not user.oauth_id and oauth_uid:
            user.oauth_id = oauth_uid
            db.session.commit()

    login_user(user)
    session.pop("sso_state", None)
    flash(f"Successfully authenticated as {user.name} via {PROVIDER_NAMES.get(provider, provider)}!", "success")
    return redirect(url_for("challenges.listing"))
