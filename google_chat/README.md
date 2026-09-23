# 💬 CTFd Google Chat Webhook Integration Plugin

An event-driven webhook notification plugin for [CTFd](https://ctfd.io/) that broadcasts tournament highlights, first bloods, solves, and team registrations directly into Google Chat spaces.

---

## ✨ Features

- **Google Chat Card V2 Formatting**:
  - Delivers styled cards with color banners, badges, and icons into your Google Chat space.
- **Configurable Event Triggers**:
  - 🩸 **First Blood Alerts**: Instant celebratory alerts when the first solver cracks a challenge.
  - 🚩 **Challenge Solves**: Live solve feed showing team name, challenge name, category, and points.
  - 👥 **Team Registrations**: Alerts when new squads register for the tournament.
  - 👤 **User Signups**: Alerts when new operators join the platform.
  - 📦 **Challenge Releases**: Announcements when new challenges are published.
- **Admin Configuration Console**:
  - Accessible via CTFd Admin Panel at `/admin/google_chat`.
  - Securely store webhook URLs in CTFd configs.
  - Test Webhook button to verify connectivity instantly.

---

## 🛠️ Setup Guide

1. In Google Chat, open your target Space and select **Apps & Integrations > Manage webhooks**.
2. Add a new incoming webhook (e.g. named `CTFd Sentinel`) and copy the generated Webhook URL.
3. In CTFd Admin Panel, navigate to `/admin/google_chat`.
4. Paste the Webhook URL into the **Google Chat Webhook URL** field.
5. Select which events to broadcast (First Bloods, Solves, Registrations).
6. Click **Send Test Message** to verify, then click **Save Settings**.

---

## 📜 Attribution

Part of the **CTFd Plugins Suite by CyberMafia** ([https://github.com/thecybermafia/ctfd-plugins](https://github.com/thecybermafia/ctfd-plugins)). Licensed under Apache 2.0 with mandatory attribution.
