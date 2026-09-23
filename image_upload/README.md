# 📸 CTFd Image Upload & Manual Review Challenge Plugin

A secure, enterprise-grade manual grading and telemetry upload challenge type for [CTFd](https://ctfd.io/). Built specifically for OSINT investigations, hardware badge challenges, physical access puzzles, writeups, and proof-of-exploitation submissions.

---

## ✨ Features

- **Participant Upload Portal**:
  - Direct file upload with optional execution methodology notes.
  - Live submission status display (`Pending Evaluation`, `Approved (+Points)`, `Rejected`).
  - Displays admin feedback directly in the challenge modal.
  - Real-time preview of submitted telemetry proof.
- **Dedicated Admin Review Console**:
  - Access at `/admin/image_uploads` directly from the CTFd admin navbar.
  - Filter submissions by challenge or review status (`Pending`, `Approved`, `Rejected`).
  - One-click file viewer with high-resolution lightbox.
  - Custom scoring slider/input to award full, partial, or bonus points.
  - Direct feedback input sent to the competitor.
- **Defensive Security & Anti-RCE Engine**:
  - Designed and audited to prevent Remote Code Execution (RCE), Stored XSS, and server-side compromise.

---

## 🔒 Defensive Security Architecture

1. **Strict File Extension Whitelist**:
   - Only standard raster images are accepted: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp`.
2. **Explicit Executable & Dangerous File Blacklist**:
   - Rejects `.svg` (prevents Stored XSS via embedded `<script>` or event handlers).
   - Rejects `.html`, `.htm`, `.xhtml`, `.xml` (prevents browser context hijacking).
   - Rejects `.php`, `.phtml`, `.py`, `.sh`, `.exe`, `.js`, `.jsp`, `.asp`, `.cgi`, etc. (prevents webshell uploads).
3. **Magic-Byte Signature Verification**:
   - Inspects the true file header bytes before saving to disk. A malicious payload disguised with a `.jpg` or `.png` extension will be immediately rejected with HTTP 400.
4. **Storage Isolation & Access Control**:
   - Uploads are saved via CTFd's internal file management subsystem.
   - External links in admin review consoles enforce `rel="noopener noreferrer"`.
   - Notes and score inputs are clamped to prevent database injection or overflows.

---

## 🛠️ Usage

1. In CTFd Admin Panel, click **Challenges > New Challenge (+)** and select **image_upload**.
2. Configure base points, maximum file size in megabytes (default: 10MB), and allowed raster formats.
3. When participants upload evidence, navigate to `/admin/image_uploads` to review submissions, grade evidence, and award points.

---

## 📜 Attribution

Part of the **CTFd Plugins Suite by CyberMafia** ([https://github.com/thecybermafia/ctfd-plugins](https://github.com/thecybermafia/ctfd-plugins)). Licensed under Apache 2.0 with mandatory attribution.
