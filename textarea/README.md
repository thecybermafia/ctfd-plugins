# 📝 CTFd Textarea Manual Review Challenge Plugin

A secure, enterprise-grade long-form text submission and manual review challenge plugin for [CTFd](https://ctfd.io/). Designed specifically for penetration testing writeups, threat intelligence reports, code analysis, incident response post-mortems, and descriptive scenario challenges.

---

## ✨ Features

- **Participant Submission Interface**:
  - Full-width monospace text area with dynamic character counter.
  - Configurable minimum and maximum character limits with instant client-side and server-side validation.
  - Configurable placeholder text guiding participants on required submission format.
  - Live submission lifecycle tracking: `Pending Review`, `Approved (+Points)`, and `Rejected`.
  - Admin feedback delivered directly inside the challenge modal.
- **Dedicated Admin Review Console**:
  - Accessible directly from the CTFd admin navbar at `/admin/textarea_submissions`.
  - Filter submissions by challenge or review status (`Pending`, `Approved`, `Rejected`).
  - Formatted writeup preview with quick one-click "Copy Writeup" button.
  - Granular scoring input with range slider to award full, partial, or bonus points (clamped between 0 and max challenge value).
  - Admin feedback textarea to leave detailed reviewer notes for the competitor.
- **Defensive Hardening & Anti-Abuse**:
  - Maximum character ceiling enforcement (up to 100,000 characters) to prevent Denial of Service (DoS) and database bloat.
  - Strict HTML escaping to eliminate Stored Cross-Site Scripting (XSS).
  - Competition lifecycle enforcement (submissions blocked when CTF is frozen, paused, or not yet started).

---

## 🔒 Defensive Security Architecture

1. **Anti-DoS Input Limits**:
   - Enforces configurable minimum and maximum character boundaries. Submissions exceeding bounds or hard ceilings (100,000 chars) are rejected with HTTP 400.
2. **Stored XSS Prevention**:
   - Writeups are rendered with strict escaping in both the admin evaluation console and participant modals.
3. **Atomic Solve & Scoring Engine**:
   - Awards are committed through CTFd's transactional solve framework (`Solves` or `Awards`), preventing double-crediting or race conditions.
4. **Access Control**:
   - Review and grading endpoints strictly require admin authorization (`@admins_only`). Competitors can only view their own submission telemetry.

---

## 🛠️ Usage

1. In the CTFd Admin Panel, click **Challenges > New Challenge (+)** and select **textarea**.
2. Specify the challenge title, category, description, and base score.
3. Configure the custom parameters:
   - **Min Characters**: Minimum length required for submission (default: 50).
   - **Max Characters**: Maximum allowed characters (default: 10,000; clamped at 100,000).
   - **Textarea Placeholder**: Guidance placeholder shown in the submission box.
4. When participants submit their reports, navigate to **Admin Panel > Submissions > Textarea Submissions** (`/admin/textarea_submissions`) to evaluate, score, and provide feedback.

---

## 📜 Attribution

Part of the **CTFd Plugins Suite by CyberMafia** ([https://github.com/thecybermafia/ctfd-plugins](https://github.com/thecybermafia/ctfd-plugins)). Licensed under Apache 2.0 with mandatory attribution.
