# 🎯 CTFd Cyber Bingo Challenge Plugin

An interactive Bingo board challenge plugin for [CTFd](https://ctfd.io/). Participants solve individual squares across a 3×3, 4×4, or 5×5 grid. Completing a horizontal row, vertical column, or diagonal grants line bonuses, while completing the entire board awards a blackout grand prize!

---

## ✨ Features

- **Dynamic Grid Sizes**: Supports 3×3 (9 tiles), 4×4 (16 tiles), and 5×5 (25 tiles).
- **Simple Admin Format**: No complex JSON needed! Configure squares with simple one-line syntax:
  ```text
  Square Title | required_flag | points (optional)
  ```
- **Real-Time Client HUD**:
  - Live progress display showing tiles solved, lines completed, and bonus points earned.
  - Interactive cybernetic board where solved tiles glow neon green.
  - Interactive tile prompt modal for entering flags square by square.
- **Automated Bonus Awarding**:
  - Automatically credits CTFd Awards for completed rows, columns, diagonals, and full-board blackouts.
  - Prevents double-claiming of line awards across users/teams.
- **Defensive Anti-Cheat**:
  - Competitor views receive sanitized tile titles and descriptions only.
  - Secret tile flags are completely stripped from API responses and DOM elements.

---

## 🛠️ Challenge Creation Guide

1. In CTFd Admin Panel, click **Challenges > New Challenge (+)** and choose **bingo**.
2. Configure base attributes:
   - **Name**: e.g., `Cyber Warfare Bingo`
   - **Category**: e.g., `Miscellaneous`
   - **Grid Size**: Choose `3 x 3`, `4 x 4`, or `5 x 5`
   - **Line Bonus**: Points awarded for every completed row, column, or diagonal (e.g., `50`).
   - **Blackout Bonus**: Extra points for completing the entire card (e.g., `250`).
   - **Bingo Squares**: Enter one square per line in the format:
     ```text
     Robots.txt | flag{robots_found}
     SQL Injection | flag{sqli_master} | 20
     Buffer Overflow | flag{rop_chain} | 30
     FREE SPACE | FREE | 0
     ```
3. Click **Create** to launch!

---

## 🔒 Security & Anti-Cheat Protections

- Flags are verified using `hmac.compare_digest` in constant time to prevent side-channel timing attacks.
- Non-admin participants cannot access `squares_text` or secret flag strings through any API endpoint (`/api/v1/challenges/<id>`).
- Submissions are rejected if the competition is paused or has not started.

---

## 📜 Attribution

Part of the **CTFd Plugins Suite by CyberMafia** ([https://github.com/thecybermafia/ctfd-plugins](https://github.com/thecybermafia/ctfd-plugins)). Licensed under Apache 2.0 with mandatory attribution.
