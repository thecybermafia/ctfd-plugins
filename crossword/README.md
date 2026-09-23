# 🔠 CTFd Cyber Crossword Challenge Plugin

A cryptographic crossword puzzle challenge type for [CTFd](https://ctfd.io/). Participants answer individual cyber clues to deduce a final master solution keyword or flag.

---

## ✨ Features

- **Intuitive Clue Configuration**: Admins configure clues simply with one line per clue:
  ```text
  Question or Clue | ANSWER
  ```
- **Local Browser Persistence**:
  - Participant guesses for each individual clue are saved locally in `localStorage` so competitors don't lose their notes across refreshes.
- **Master Keyword Submission**:
  - Players deduce the final answer word from the clues and submit it via the primary challenge submission bar.
- **Defensive Anti-Cheat**:
  - Clue answers are hidden from the player. The API and DOM only provide clue hints and letter lengths (e.g., `(5 letters)`), preventing reverse engineering of answers from page source.
  - Constant-time verification prevents side-channel timing attacks.

---

## 🛠️ Challenge Creation Guide

1. In CTFd Admin Panel, click **Challenges > New Challenge (+)** and choose **crossword**.
2. Fill in challenge details:
   - **Name**: e.g., `Decryption Crossword`
   - **Points**: Points awarded for solving the master flag.
   - **Solution Word or Flag**: Secret keyword or flag (e.g., `CYBERDEFENSE` or `flag{crypto_master}`).
   - **Clues & Answers**:
     ```text
     Protocol for secure web browsing | HTTPS
     Malicious self-replicating program | WORM
     Unique numerical network identifier | IP
     Database query injection attack | SQLI
     Linux superuser privilege command | SUDO
     Asymmetric cryptography algorithm | RSA
     ```
3. Click **Create**.

---

## 🔒 Security & Anti-Cheat Protections

- All clue answers and solution words are protected on the server side.
- Non-admin users querying `/api/v1/challenges/<id>` receive only the sanitized clue text and length.
- Flag evaluation uses `hmac.compare_digest`.

---

## 📜 Attribution

Part of the **CTFd Plugins Suite by CyberMafia** ([https://github.com/thecybermafia/ctfd-plugins](https://github.com/thecybermafia/ctfd-plugins)). Licensed under Apache 2.0 with mandatory attribution.
