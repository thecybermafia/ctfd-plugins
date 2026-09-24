# 🔐 CTFd Enterprise Single Sign-On (SSO) Plugin

A robust, enterprise-grade Single Sign-On (SSO) and identity federation plugin for [CTFd](https://ctfd.io/). Supports major OAuth2, OpenID Connect (OIDC), and SAML 2.0 identity providers with mandatory SSO policy enforcement, auto-provisioning, and automated registration visibility synchronization.

---

## ✨ Features

- **Multi-Provider Identity Federation**:
  - **Disable SSO**: Standard CTFd local credential authentication.
  - **SAML 2.0**: Enterprise identity providers (Okta SAML, Shibboleth, Active Directory ADFS, OneLogin).
  - **Discord**: OAuth2 integration with Discord guilds and accounts.
  - **GitHub**: OAuth2 authentication via GitHub accounts or enterprise organizations.
  - **Google**: OAuth2 / OpenID Connect federation via Google Workspace or consumer accounts.
  - **Azure (Microsoft Entra ID)**: Enterprise directory authentication via Microsoft Azure tenants.
  - **Okta**: OAuth2 / OIDC authentication via custom Okta domains.
- **Granular User Enforcement Policies**:
  - **All Users**: Mandatory SSO for all participants and administrators. Local password logins are blocked.
  - **Admins Only**: Enforces SSO specifically for privileged administrator accounts while leaving standard competitor logins flexible.
- **Automated Registration Visibility Sync**:
  - Setting User Settings to **All Users** automatically synchronizes CTFd's **Registration Visibility** to **Private** to prevent unauthorized public account creation bypassing corporate identity vetting.
  - Interactive warning banner in the Admin Console alerting administrators if registration is public when SSO is required.
- **Fail-Safe Disaster Recovery**:
  - Built-in emergency administrative bypass query (`/login?emergency_auth=true`) allowing authorized administrators with root database/console access to log in with emergency local credentials in case of third-party IdP outages.
- **Automated User Provisioning**:
  - Automatically provisions verified CTFd user profiles upon successful identity assertion, extracting name, email, and authentication tokens.

---

## 🛠️ Configuration & Usage

### 1. Admin Console Setup
1. Log into your CTFd instance as an administrator.
2. In the Admin Panel navbar, click **Plugins > SSO Settings** (`/admin/sso`).
3. Select your desired **Single Sign-On Provider**:
   - `Disable SSO`
   - `SAML`
   - `Discord`
   - `GitHub`
   - `Google`
   - `Azure`
   - `Okta`
4. Expand the credentials panel and enter the required Client ID, Client Secret, endpoints, or IdP Metadata XML.
5. Select your **User Settings** policy:
   - **All Users** *(auto-sets Registration Visibility to Private)*
   - **Admins Only**
6. Select your **Registration Visibility**:
   - **Public**
   - **Private**
7. Click **Save SSO Configuration**.

---

## 🔒 Defensive Security Architecture

1. **State & CSRF Token Validation**:
   - OAuth flows generate and verify cryptographic `state` parameters stored in the session to prevent login CSRF attacks.
2. **Strict Redirection Whitelist**:
   - Post-authentication redirects validate host boundaries to eliminate Open Redirect vulnerabilities.
3. **Registration Policy Lockout Defense**:
   - Synchronizes `registration_visibility = "private"` when SSO is mandatory for all users, closing race conditions where adversaries register unmanaged local accounts.
4. **Emergency Disaster Recovery Channel**:
   - The emergency bypass parameter (`?emergency_auth=true`) requires valid admin credentials and does not weaken standard authentication checks.

---

## 📜 Attribution

Part of the **CTFd Plugins Suite by CyberMafia** ([https://github.com/thecybermafia/ctfd-plugins](https://github.com/thecybermafia/ctfd-plugins)). Licensed under Apache 2.0 with mandatory attribution.
