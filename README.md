# 🧩 CTFd Advanced Plugins Suite

A production-ready collection of game-changing challenge types and operational integrations for [CTFd](https://ctfd.io/), engineered and defensively hardened.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Security Audited](https://img.shields.io/badge/Security%20Audit-Defensively%20Hardened-brightgreen.svg)](#security-audit--defensive-hardening)
[![CTFd Compatibility](https://img.shields.io/badge/CTFd-v3.5%20--%20v3.8%2B-orange.svg)](https://github.com/CTFd/CTFd)

---

## 📦 Included Plugins

| Plugin | Type | Description |
| :--- | :--- | :--- |
| [**`referrals`**](./referrals) | Community & Growth | Gamified player recruitment system with proof-of-play milestone qualification, anti-cheat IP/subnet quarantine, teammate collusion shields, and super-configurable admin controls. |
| [**`plugin_manager`**](./plugin_manager) | Administration | Dynamic plugin enable/disable manager with nested admin dropdown menu organization and core plugin protections. |
| [**`bingo`**](./bingo) | Challenge Type | Tactical 5x5 Defense Matrix Cockpit HUD with neon channel indicators (B-I-N-G-O), side-by-side Target Interrogation console, keyword/flag daubing, real-time vector completion telemetry, and blackout prizes. |
| [**`phishing_inbox`**](./phishing_inbox) | Challenge Type | Split-pane webmail triage terminal with sandboxed iframe CSP email preview, forensic headers (SPF, DKIM, DMARC), safe link inspection, and triage workflows. |
| [**`cyber_wordle`**](./cyber_wordle) | Challenge Type | Tactical 5-letter cybersecurity terminology decryptor with letter flip animations, letter frequency validation, physical and virtual on-screen keyboards. |
| [**`quiz_challenges`**](./quiz_challenges) | Challenge Type | Single-choice radio and multi-select checkbox tactical assessments, deterministic choice shuffling, and post-solve educational explanations. |
| [**`red_flag_hotspot`**](./red_flag_hotspot) | Challenge Type | Visual recon inspection with Euclidean distance thresholds and letterbox-safe coordinate tracking. |
| [**`url_anatomy`**](./url_anatomy) | Challenge Type | RFC 3986 token dissector with live Punycode/Unicode toggle for IDN homoglyph analysis. |
| [**`incident_sequence`**](./incident_sequence) | Challenge Type | Containment/eradication timeline sequencer with prohibited countermeasure isolation and deterministic distractor shuffling. |
| [**`branching_scenario`**](./branching_scenario) | Challenge Type | Dialogue-driven crisis decision simulator with server-side graph traversal verification. |
| [**`crossword`**](./crossword) | Challenge Type | Cyber Crossword puzzle challenge with simple `Clue \| Answer` setup, master solution keyword verification, and HMAC comparison. |
| [**`image_upload`**](./image_upload) | Challenge Type | Secure manual review challenge for OSINT, physical hacking, hardware badges, and telemetry proof with admin scoring console. |
| [**`textarea`**](./textarea) | Challenge Type | Monospace long-form text submission and manual evaluation challenge with character counter, DoS clamping, and admin review console. |
| [**`sso`**](./sso) | Authentication | Enterprise Single Sign-On supporting SAML 2.0, Discord, GitHub, Google, Azure, and Okta with policy enforcement and private registration sync. |
| [**`chat_notifications`**](./chat_notifications) | Webhooks & Broadcasts | Real-time notifications and webhooks for Discord, Slack, Teams, Google Chat, Telegram, and Generic Webhooks with independent dual-channel routing and HMAC SHA-256 signatures. |

---

## 🛡️ Security Audit & Defensive Hardening

Every plugin in this suite has undergone a comprehensive defensive security audit and has been tested against real-world adversarial attacks:

1. **Anti-Cheat & Flag Leakage Prevention**:
   - **Bingo**: Tile answers and flags are strictly guarded. Competitors only receive sanitized board titles and descriptions; secret tile flags are never exposed in API payloads or DOM. In addition, all 25 tiles support robust keyword and alias matching (case-insensitive, whitespace-trimmed).
   - **Cyber Wordle**: Future guess rows are held strictly in memory and are never rendered into the client DOM until reached, completely blocking DevTools DOM-inspection or bypass attempts.
   - **Quiz Challenges**: Serializes both list-of-strings and dictionary option configurations cleanly, preventing 500 errors on legacy challenge formats.
   - **Crossword**: Clue answers are completely stripped from competitor responses. Only clue hints and letter lengths are sent to the client.
2. **Timing Attack Resistance**:
   - String and flag verification uses constant-time comparisons via `hmac.compare_digest` to prevent side-channel timing attacks.
3. **Upload Hardening & Anti-RCE (Image Upload)**:
   - **Strict Whitelist**: Accepts only safe raster image extensions (`png`, `jpg`, `jpeg`, `webp`, `gif`, `bmp`).
   - **Dangerous Extension Blacklist**: Blocks executable and scriptable extensions (`svg`, `html`, `php`, `py`, `js`, `exe`, etc.) to eliminate Stored XSS and remote code execution risks.
   - **Magic Bytes Validation**: Verifies the genuine byte signatures of image payloads to stop disguised webshells.
   - **Input Sanitization**: Score inputs and notes are clamped to prevent database injection and DoS.
4. **Input Boundary Enforcement & XSS Elimination (Textarea)**:
   - Submissions are clamped to configurable character thresholds and a hard 50,000-character ceiling to prevent DoS.
   - Writeups are strictly escaped in both the admin scoring console and user modals to prevent Stored XSS.
5. **SSO Policy Synchronization & Authentication Lockdown (SSO)**:
   - Synchronizes `registration_visibility = "private"` when SSO is mandatory for all users, closing race conditions where unmanaged accounts could be registered publicly.
   - Rejects password logins when SSO is required, with an emergency admin recovery bypass (`?emergency_auth=true`) for disaster response.
   - Explicitly rejects XML `DOCTYPE` and `ENTITY` declarations to protect SAML workflows from XXE and entity expansion attacks.
6. **Multi-Vector Anti-Cheat & Sybil Protection (Referrals)**:
   - Blocks self-referrals, matching email addresses, circular referral loops (`A -> B -> A`), and teammate self-farming.
   - Restricts onboarding linkers to the initial 5-minute registration window, preventing retro-claiming by aged accounts.
   - Proof-of-play milestones prevent reward allocation to inactive dummy accounts.
   - IP matching and subnet CIDR screening automatically flags suspected multi-accounting into administrative quarantine.
   - Auto-revokes awarded scoreboard bonus points if recruit accounts are banned or hidden.
7. **Privilege Boundary & Safe Execution (Plugin Manager)**:
   - Strictly validates plugin names against known filesystem manifests to eliminate path traversal.
   - Prevents disablement of core CTFd functional plugins (`challenges`, `flags`, `plugin_manager`).
8. **CTF Lifecycle Enforcement**:
   - Solves and submissions are blocked if the competition is frozen, paused, or has not started yet (unless submitted by an admin).
   - Hidden challenges cannot be queried or solved by non-admin participants.
9. **Global JavaScript Namespace Isolation**:
   - Client scripts across all challenge types employ scoped variables and challenge-specific retry counters (`seqRetryCount`, `scenarioRetryCount`, `bingoRetryCount`), eliminating global variable redeclaration errors during rapid modal transitions.

---

## 🚀 Installation Guide

### Option 1: Standard / Self-Hosted CTFd Installation
 
1. Copy the desired plugin folder(s) directly into your CTFd `CTFd/plugins/` directory:
   ```bash
   # Copy all plugins
   cp -r referrals plugin_manager bingo crossword image_upload textarea sso chat_notifications /path/to/CTFd/CTFd/plugins/
   ```

2. Restart your CTFd application or container:
   ```bash
   docker compose restart ctfd
   # Or for systemd / gunicorn:
   sudo systemctl restart ctfd
   ```

### Option 2: CTFd Enterprise Cloud / Hosted CTFd Installation

CTFd Cloud requires each plugin to be uploaded **individually as its own separate ZIP file**.
The archive must contain **exactly one top-level directory** matching the plugin name (e.g. `bingo/`), and that directory must directly contain `__init__.py`:
- Uploading the multi-plugin bundle triggers: *"Zip is missing an __init__.py file"*
- Uploading multiple loose directories triggers: *"Zip contains multiple top-level directories"*

#### Automated Packaging (Recommended)
Run the automated packaging utility to compile and validate all 15 plugins into `dist/plugins/`:
```bash
python3 scripts/build_cloud_zips.py
```
Pre-packaged ZIPs will be generated in `dist/plugins/`:
- `dist/plugins/bingo.zip`
- `dist/plugins/crossword.zip`
- `dist/plugins/cyber_wordle.zip`
- `dist/plugins/phishing_inbox.zip`
- `dist/plugins/quiz_challenges.zip`
- *(and all other challenge/utility plugins)*

#### Manual Packaging Command
From the repository root, package any single plugin directory:
```bash
zip -r bingo.zip bingo -x "*.DS_Store*" "*__pycache__*"
```

#### Uploading to CTFd Cloud
1. Navigate to **Instance Management > Plugins > Upload Plugin**.
2. Select your plugin ZIP (e.g. `dist/plugins/bingo.zip`, `dist/plugins/crossword.zip`, etc.).
3. Upload each plugin you need individually.



---

## 📜 Attribution & License

This project is licensed under the **Apache License 2.0** with mandatory attribution.

### Attribution Requirements (Section 4d of Apache 2.0)
You are free to use, fork, and modify this software provided that:
1. **Notice File**: You must preserve the `NOTICE` file in all redistributions and derivative works.
2. **Prominent Credit**: When deploying this software in a public CTF competition or distributing modified versions, visible attribution must be maintained:
   ```markdown
   Powered by CTFd Plugins Suite (https://github.com/thecybermafia/ctfd-plugins)
   ```
3. **State Changes**: Any modified files must carry prominent notices documenting that changes were made.

See [LICENSE](LICENSE) and [NOTICE](NOTICE) for full terms.
