# CTFd Operative Recruitment & Anti-Cheat Referral Plugin

An enterprise-grade, gamified referral and player recruitment plugin for CTFd designed to attract active competitors while preventing bot farming, self-referral, and team point collusion.

---

## ⚡ Key Capabilities

- **Strict Onboarding Window**: Links referrals seamlessly via URL query parameters (`?ref=...`), persistent cookies, or session memory during local signup and SSO (Discord, GitHub, SAML OAuth). Ineligible after onboarding.
- **Proof-of-Play Qualification Milestone**: Eliminates disposable ghost account farming. Zero points are awarded upon registration; bonus points unlock only after the recruit reaches an admin-configured challenge point milestone (e.g. $\ge 100$ PTS) and solve count.
- **Team Mode Anti-Collusion**: Points are awarded to the Referrer's Team, teammates are strictly prohibited from referring each other, and bonus caps are enforced at the Team level.
- **Multi-Layered Anti-Cheat Screening**:
  - Self-referral and matching email detection.
  - Circular referral loop prevention (`A -> B -> A`).
  - IP and subnet collision detection with automatic `FLAGGED` quarantine for administrative review.
  - Per-account and global competition point inflation ceilings.
  - Scoreboard point auto-revocation on recruit penalties.
- **Super-Configurable Admin Panel (`/admin/referrals`)**: Live telemetry KPI cards, filterable audit roster with IP verification badges, 1-click Approve/Revoke controls, and comprehensive settings.
- **Tactical Participant Hub (`/referrals`)**: Modern directive dashboard with 1-click clipboard copy, real-time milestone progress bars, and recruited operatives roster. Full Dark & Light theme parity.

---

## 🚀 Installation

1. Copy the `referrals/` directory into your CTFd plugins folder:
   ```bash
   cp -r referrals /opt/CTFd/CTFd/plugins/
   ```
2. Restart your CTFd instance:
   ```bash
   docker compose restart ctfd
   ```
3. Access `/admin/referrals` to configure your recruitment directive parameters!

---

## 📜 License
Apache-2.0
