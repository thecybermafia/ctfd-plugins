# CTFd Operative Recruitment & Anti-Cheat Referral System

An enterprise-grade, gamified referral and player recruitment plugin for CTFd designed to attract active competitors while preventing bot farming, self-referral, and team point collusion.

---

## Key Features & Architecture

### 1. Dual Mode Support (User & Team CTF Modes)
- **User Mode**: Awards and referral telemetry are tracked directly at the individual competitor level.
- **Team Mode**:
  - The team captain holds the primary team directive invite code.
  - Bonus points minted are credited to the recruiter team's scoreboard standing.
  - Per-account caps are enforced at the entire team level to prevent syndicates from churning dummy accounts.
  - Teammates are strictly barred from referring one another to farm points.
  - Recruited teams are displayed directly in the admin team telemetry view (`/admin/teams/<id>`).

### 2. Proof-of-Play Qualification Modes (Recruit Training)
To completely eliminate disposable ghost/bot account farming, **zero points are awarded upon registration**. Recruits must prove genuine field capability before bonus points unlock for either party:
- **`points_only`**: Recruit must reach an admin-defined challenge score threshold (e.g. $\ge 100$ PTS) across a minimum solve count.
- **`challenge_only`**: Recruit must solve a specific designated challenge (e.g. "Sanity Check", "Welcome Challenge", or an onboarding challenge).
- **`both`**: Recruit must reach both the point threshold **and** solve the designated challenge.
- **`either`**: Recruit qualifies if they either meet the point threshold **or** solve the designated challenge.
- Optional exclusion of 0-point informational challenges from milestone calculations.

### 3. Referrer Access Gate & Eligibility Gate
Admins can gate access to the recruitment program so only verified, active competitors can generate invite codes and access the referral terminal:
- **`none`**: Open to all registered competitors immediately.
- **`points`**: Requires the operative to earn a minimum challenge score (e.g. $\ge 50$ PTS).
- **`solves`**: Requires solving a minimum number of distinct challenges.
- **`challenge`**: Requires solving a specific prerequisite challenge.
- **`all`**: Requires meeting points, solves, and the prerequisite challenge.
- **`any`**: Unlocks if any of the configured criteria are satisfied.

### 4. Dynamic Access Control & Navigation Protection
- When disabled, paused, or when an operative fails the Referrer Access Gate:
  - The **Referrals** link is automatically hidden from the top navigation bar.
  - The **Referrals** tab is completely removed from `/settings`.
  - Direct visits to `/referrals` are immediately intercepted and redirected to `/settings` with an admin-customizable warning notice (e.g. `"ACCESS RESTRICTED: Operative clearance level insufficient. Solve challenges to earn ≥ 50 points first."`).
  - API calls to `/api/v1/referrals/me` return `403 Forbidden` with `{ "locked": true }`.

### 5. Multi-Layered Anti-Cheat & Security Shields
- **Seamless Onboarding Linker**: Captures invite codes via URL parameter (`?ref=...`), secure HTTP-only cookies, or session memory during local signup and SSO (Discord, GitHub, Google, Okta, Azure, SAML OAuth). Only allows linking during the recent registration onboarding window (first 5 minutes).
- **Self-Referral Prevention**: Operatives cannot link their own codes or use matching email addresses.
- **Circular Referral Prevention**: Blocks recursive exploitation loops (`A recruits B`, so `B` cannot recruit `A`).
- **One-Time Recruitment**: An account can only be recruited once across its entire lifecycle.
- **IP & Subnet Screening**: Identifies identical IP connections and local subnet collisions (`/24 CIDR`). Configurable policies:
  - `Flag & Hold`: Holds referral in quarantine with a `FLAGGED` status for admin review.
  - `Block`: Strict rejection.
  - `Allow`: Permissive mode for local LAN testing.
- **Sanction Synchronization**: If a recruited operative or team is banned or hidden, any awarded referral bonus points are automatically stripped from scoreboard standings.
- **Inflation Caps**: Configurable per-account referral limit and competition-wide global bonus point ceiling.

### 6. Administrative Operations & Management (`/admin/referrals`)
- **Live Recruitment Telemetry**: Real-time KPI summary cards (Active Codes, Total Recruits, In Training, Qualified, Fraud Flags, Points Minted).
- **Audit Roster**: Inspect recruiter, recruit, IP matching status, solve count progress, and current state. 1-click Approve Flagged, Revoke Bonus, or Delete.
- **User & Team Exclusions**: Suspend specific users or teams from participating in referrals by ID or exact name with 1-click re-enablement.
- **Custom Referral Codes**: Admins can assign custom alphanumeric referral vanity codes to players or teams.
- **Integrated Admin Views**: Embedded referral history and metrics inside CTFd's core admin pages (`/admin/users/<id>` and `/admin/teams/<id>`).

---

## Configuration Reference

| Setting Key | Default | Description |
|---|---|---|
| `referral_enabled` | `true` | Master switch for the recruitment system. |
| `referral_show_in_navbar` | `false` | When false, referrals are tucked into `/settings > Referrals`. |
| `referral_broadcast_feed` | `true` | Announce qualified recruit milestones in the tactical live activity feed. |
| `referral_access_denied_message` | `...` | Custom notice flashed to operatives attempting to access `/referrals` when locked. |
| `referral_program_name` | `Operative Recruitment Directive` | Title displayed on participant dashboards. |
| `referral_points` | `100` | Points minted to the recruiter operative upon recruit qualification. |
| `referral_max_per_account` | `5` | Maximum number of rewarded referrals allowed per account or team (0 = unlimited). |
| `referral_global_point_cap` | `0` | Total referral points allowed across entire CTF (0 = unlimited). |
| `referral_referee_bonus_enabled` | `true` | Award a welcome bonus to recruit upon proving capability. |
| `referral_referee_bonus_points` | `25` | Welcome points awarded to recruit upon reaching qualification threshold. |
| `referral_qualification_mode` | `points_only` | Qualification mode: `points_only`, `challenge_only`, `both`, `either`. |
| `referral_required_challenge_id`| `""` | Designated challenge required for recruit qualification. |
| `referral_min_points_to_qualify`| `100` | Minimum challenge points recruit must score to unlock bonuses. |
| `referral_min_solves_to_qualify` | `1` | Minimum distinct challenge solves count required to qualify. |
| `referral_unlock_mode` | `none` | Referrer eligibility gate: `none`, `points`, `solves`, `challenge`, `all`, `any`. |
| `referral_unlock_challenge_id` | `""` | Prerequisite challenge required to unlock recruitment privileges. |
| `referral_unlock_min_points` | `0` | Score required to unlock referral terminal. |
| `referral_unlock_min_solves` | `0` | Solves count required to unlock referral terminal. |
| `referral_ip_policy` | `flag` | Policy for identical IPs: `flag`, `block`, or `allow`. |
| `referral_disallow_teammates` | `true` | Disallow players from referring members of their own syndicate team. |
| `referral_auto_revoke_on_ban` | `true` | Strip awarded points if recruit is banned or hidden. |

---

## Installation & Deployment

1. Copy the `referrals/` directory into your CTFd plugins directory:
   ```bash
   cp -r referrals /opt/CTFd/CTFd/plugins/
   ```
2. Restart CTFd:
   ```bash
   docker compose restart ctfd
   ```
3. Navigate to **Plugins > Referrals** (`/admin/referrals`) to customize your parameters.

---

## License
Apache-2.0
