# 🧩 CTFd Advanced Plugins Suite

A production-ready collection of game-changing challenge types and operational integrations for [CTFd](https://ctfd.io/), engineered and defensively hardened by **CyberMafia**.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Security Audited](https://img.shields.io/badge/Security%20Audit-Defensively%20Hardened-brightgreen.svg)](#security-audit--defensive-hardening)
[![CTFd Compatibility](https://img.shields.io/badge/CTFd-v3.5%20--%20v3.8%2B-orange.svg)](https://github.com/CTFd/CTFd)

---

## 📦 Included Plugins

| Plugin | Type | Description |
| :--- | :--- | :--- |
| [**`bingo`**](./bingo) | Challenge Type | Interactive 3×3, 4×4, or 5×5 Cyber Bingo board with instant tile validation, row/col/diagonal line bonuses, and blackout prizes. |
| [**`crossword`**](./crossword) | Challenge Type | Cyber Crossword puzzle challenge with simple `Clue \| Answer` setup and master solution keyword verification. |
| [**`image_upload`**](./image_upload) | Challenge Type | Secure manual review challenge for OSINT, physical hacking, hardware badges, and telemetry proof with admin scoring console. |
| [**`textarea`**](./textarea) | Challenge Type | Monospace long-form text submission and manual evaluation challenge with character counter, DoS clamping, and admin review console. |
| [**`sso`**](./sso) | Authentication | Enterprise Single Sign-On supporting SAML 2.0, Discord, GitHub, Google, Azure, and Okta with policy enforcement and private registration sync. |
| [**`google_chat`**](./google_chat) | Admin Integration | Real-time webhook notifications to Google Chat spaces for First Bloods, challenge solves, and team registrations. |

---

## 🛡️ Security Audit & Defensive Hardening

Every plugin in this suite has undergone a comprehensive defensive security audit and has been tested against real-world adversarial attacks:

1. **Anti-Cheat & Flag Leakage Prevention**:
   - **Bingo**: Tile answers and flags are strictly guarded. Competitors only receive sanitized board titles and descriptions; secret tile flags are never exposed in API payloads or DOM.
   - **Crossword**: Clue answers are completely stripped from competitor responses. Only clue hints and letter lengths are sent to the client.
2. **Timing Attack Resistance**:
   - String and flag verification uses constant-time comparisons via `hmac.compare_digest` to prevent side-channel timing attacks.
3. **Upload Hardening & Anti-RCE (Image Upload)**:
   - **Strict Whitelist**: Accepts only safe raster image extensions (`png`, `jpg`, `jpeg`, `webp`, `gif`, `bmp`).
   - **Dangerous Extension Blacklist**: Blocks executable and scriptable extensions (`svg`, `html`, `php`, `py`, `js`, `exe`, etc.) to eliminate Stored XSS and remote code execution risks.
   - **Magic Bytes Validation**: Verifies the genuine byte signatures of image payloads to stop disguised webshells.
   - **Input Sanitization**: Score inputs and notes are clamped to prevent database injection and DoS.
4. **Input Boundary Enforcement & XSS Elimination (Textarea)**:
   - Submissions are clamped to configurable character thresholds and a hard 100,000-character ceiling to prevent DoS.
   - Writeups are strictly escaped in both the admin scoring console and user modals to prevent Stored XSS.
5. **SSO Policy Synchronization & Authentication Lockdown (SSO)**:
   - Synchronizes `registration_visibility = "private"` when SSO is mandatory for all users, closing race conditions where unmanaged accounts could be registered publicly.
   - Rejects password logins when SSO is required, with an emergency admin recovery bypass (`?emergency_auth=true`) for disaster response.
6. **CTF Lifecycle Enforcement**:
   - Solves and submissions are blocked if the competition is frozen, paused, or has not started yet (unless submitted by an admin).
   - Hidden challenges cannot be queried or solved by non-admin participants.

---

## 🚀 Installation Guide

### Option 1: Standard CTFd Installation

1. Copy the desired plugin folder(s) directly into your CTFd `CTFd/plugins/` directory:
   ```bash
   # Copy all plugins
   cp -r bingo crossword image_upload textarea sso google_chat /path/to/CTFd/CTFd/plugins/
   ```

2. Restart your CTFd application or container:
   ```bash
   docker compose restart ctfd
   # Or for systemd / gunicorn:
   sudo systemctl restart ctfd
   ```

3. Navigate to **Admin Panel > Challenges > New Challenge (+)**. You will see the new challenge types available in the dropdown:
   - `bingo`
   - `crossword`
   - `image_upload`
   - `textarea`

---

## 📜 Attribution & License

This project is licensed under the **Apache License 2.0** with mandatory attribution.

### Attribution Requirements (Section 4d of Apache 2.0)
You are free to use, fork, and modify this software provided that:
1. **Notice File**: You must preserve the `NOTICE` file in all redistributions and derivative works.
2. **Prominent Credit**: When deploying this software in a public CTF competition or distributing modified versions, visible attribution must be maintained:
   ```markdown
   Powered by CTFd Plugins Suite by CyberMafia (https://github.com/thecybermafia/ctfd-plugins)
   ```
3. **State Changes**: Any modified files must carry prominent notices documenting that changes were made.

See [LICENSE](LICENSE) and [NOTICE](NOTICE) for full terms.
