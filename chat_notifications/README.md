# Universal Chat & Webhook Notifications Plugin for CTFd

Enterprise real-time notification engine for CTFd competitions with native multi-platform dispatch adapters.

## Supported Platforms
- **Discord**: Rich Embeds with color coding (Green for Solves, Gold for First Blood, Red for Admin Alerts, Cyan for Releases) and inline fields.
- **Slack / Mattermost**: Formatted Block Kit headers, mrkdwn sections, and attachments.
- **Microsoft Teams**: Adaptive Cards 1.4 & Office 365 MessageCards with status facts and badges.
- **Google Chat**: CardsV2 interactive widgets and structured text chips.
- **Telegram**: Direct bot integration via `chat_id` and formatted HTML messages.
- **Generic Custom Webhook**: Standard structured JSON schema with event types and timestamps.

## Features
- **Independent Dual-Channel Routing**:
  - **Participant Channel**: Public competitor stream for announcements, challenge unlocks, first bloods, solves, and registrations.
  - **Admin Operations Channel**: Internal operations stream for proctoring, registrations, manual reviews (`textarea` and `image_upload`), and referral anti-cheat alerts.
- **Auto-Detection**: Pasting any webhook URL automatically resolves the target provider.
- **Asynchronous & Resilient**: Database transactions commit before webhooks fire, preventing first-blood race conditions and keeping API latencies near-zero.
- **SSRF Hardened**: Restricts delivery to valid public HTTP/HTTPS endpoints and blocks loopback/private ranges.
