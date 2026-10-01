CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

function initPhishingInbox() {
  const chalIdEl = document.getElementById("challenge-id");
  const inboxContainer = document.querySelector(".phishing-inbox-container");
  if (!chalIdEl || !inboxContainer) return false;

  const challengeId = chalIdEl.value;
  const emailsJsonEl = document.getElementById("inbox-emails-json");
  const chalInput = document.getElementById("challenge-input");
  const reviewedCountEl = document.getElementById("inbox-reviewed-count");
  const submitBtn = document.getElementById("challenge-submit");
  const urlStatusBar = document.getElementById("url-status-bar");
  const toggleHeadersBtn = document.getElementById("toggle-headers-btn");
  const headersPanel = document.getElementById("email-headers-panel");
  const activeCounterEl = document.getElementById("gmail-active-counter");

  let emails = [];
  if (emailsJsonEl && emailsJsonEl.textContent) {
    try {
      emails = JSON.parse(emailsJsonEl.textContent);
    } catch (e) {
      console.error("Failed to parse emails from JSON element:", e);
    }
  }

  if ((!emails || emails.length === 0) && CTFd._internal.challenge.data && CTFd._internal.challenge.data.emails_data) {
    emails = CTFd._internal.challenge.data.emails_data;
  }

  if (!emails || emails.length === 0) return false;

  const storageKey = `ctfd_phishing_inbox_${challengeId}`;
  let userActions = {};
  try {
    userActions = JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch (e) {
    userActions = {};
  }

  let currentEmailId = emails[0].id;

  // Google account circle colors
  function getGoogleAvatarColor(str) {
    const colors = ["#1a73e8", "#e37400", "#0f9d58", "#a142f4", "#d93025", "#129eaf", "#e8710a", "#3949ab"];
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  }

  // Colorize mini avatars in list
  document.querySelectorAll(".gmail-avatar-circle").forEach((av) => {
    const sender = av.getAttribute("data-sender") || "";
    av.style.backgroundColor = getGoogleAvatarColor(sender);
  });

  // Toggle Gmail 'to me' details popover
  if (toggleHeadersBtn && headersPanel && !toggleHeadersBtn.dataset.bound) {
    toggleHeadersBtn.dataset.bound = "true";
    toggleHeadersBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = headersPanel.style.display !== "none";
      headersPanel.style.display = isVisible ? "none" : "block";
    });

    document.addEventListener("click", (e) => {
      if (headersPanel.style.display !== "none" && !headersPanel.contains(e.target) && e.target !== toggleHeadersBtn) {
        headersPanel.style.display = "none";
      }
    });
  }

  function getStatusLabel(action) {
    switch (action) {
      case "report":
        return { label: "🚩 REPORTED", badgeClass: "bg-danger" };
      case "safe":
        return { label: "🛡️ SAFE", badgeClass: "bg-success" };
      case "delete":
        return { label: "🗑️ TRASHED", badgeClass: "bg-secondary" };
      default:
        return { label: "PENDING", badgeClass: "bg-secondary" };
    }
  }

  function updateListBadges() {
    let reviewed = 0;
    emails.forEach((em) => {
      const act = userActions[em.id];
      const badge = document.querySelector(`.inbox-item-status-badge[data-email-id="${em.id}"]`);
      if (act) {
        reviewed++;
        if (badge) {
          const info = getStatusLabel(act);
          badge.textContent = info.label;
          badge.className = `inbox-item-status-badge badge ${info.badgeClass} font-monospace`;
        }
      } else if (badge) {
        badge.textContent = "PENDING";
        badge.className = "inbox-item-status-badge badge bg-secondary font-monospace";
      }
    });

    if (reviewedCountEl) {
      reviewedCountEl.textContent = reviewed;
    }

    if (chalInput) {
      chalInput.value = JSON.stringify(userActions);
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (submitBtn) {
      const allDone = emails.length > 0 && reviewed >= emails.length;
      submitBtn.disabled = !allDone;
      if (allDone) {
        submitBtn.classList.add("shadow");
      }
    }
  }

  function renderActiveEmail(emailId) {
    const emIdx = emails.findIndex((e) => e.id === emailId);
    const em = emIdx >= 0 ? emails[emIdx] : emails[0];
    if (!em) return;
    currentEmailId = em.id;

    // Close details popover if open
    if (headersPanel) headersPanel.style.display = "none";

    // Update active counter
    if (activeCounterEl) {
      activeCounterEl.textContent = `${(emIdx >= 0 ? emIdx : 0) + 1} of ${emails.length}`;
    }

    // Update list selection state
    document.querySelectorAll(".gmail-item-row").forEach((card) => {
      const isCur = card.getAttribute("data-email-id") === em.id;
      card.classList.toggle("active", isCur);
    });

    // Populate header info
    const subjEl = document.getElementById("active-email-subject");
    const senderEl = document.getElementById("active-email-sender");
    const senderAddrEl = document.getElementById("active-email-sender-addr");
    const senderFullEl = document.getElementById("active-email-sender-full");
    const dateEl = document.getElementById("active-email-date");
    const fullDateEl = document.getElementById("active-email-full-date");
    const detailsSubjEl = document.getElementById("active-email-details-subject");
    const avatarEl = document.getElementById("active-email-avatar");
    const replyToEl = document.getElementById("active-email-reply-to");
    const authBadgesContainer = document.getElementById("active-email-auth-badges");
    const attachSection = document.getElementById("active-email-attachments");
    const attachContainer = document.getElementById("attachments-container");
    const bodyEl = document.getElementById("active-email-body-content");

    const senderDisplay = em.sender_name || em.sender_email || "Unknown Sender";
    const senderAddr = em.sender_email || "unknown@domain.com";

    if (subjEl) subjEl.textContent = em.subject || "No Subject";
    if (detailsSubjEl) detailsSubjEl.textContent = em.subject || "No Subject";
    if (senderEl) senderEl.textContent = senderDisplay;
    if (senderAddrEl) senderAddrEl.textContent = `<${senderAddr}>`;
    if (senderFullEl) senderFullEl.textContent = `${senderDisplay} <${senderAddr}>`;
    if (dateEl) dateEl.textContent = em.date || "Today";
    if (fullDateEl) fullDateEl.textContent = em.date || "Today, 09:15 AM";
    if (replyToEl) replyToEl.textContent = em.reply_to || senderAddr;

    // Large Google Account Circle Avatar
    if (avatarEl) {
      avatarEl.textContent = senderDisplay.trim().charAt(0).toUpperCase();
      avatarEl.style.backgroundColor = getGoogleAvatarColor(senderDisplay);
    }

    // Auth badges inside 'to me' popover (factual technical data only, no cheat banner)
    if (authBadgesContainer) {
      authBadgesContainer.innerHTML = "";
      if (em.auth_results && Object.keys(em.auth_results).length > 0) {
        Object.entries(em.auth_results).forEach(([proto, status]) => {
          const st = String(status).toUpperCase();
          const badge = document.createElement("span");
          badge.className = `badge ${st === "PASS" ? "bg-success" : "bg-danger"} font-monospace`;
          badge.style.fontSize = "0.68rem";
          badge.textContent = `${proto.toUpperCase()}: ${st}`;
          authBadgesContainer.appendChild(badge);
        });
      } else {
        authBadgesContainer.innerHTML = `<span class="text-muted small">Standard internal delivery</span>`;
      }
    }

    // Attachments: Clean Gmail Attachment Chips (no spoiler badges!)
    if (attachSection && attachContainer) {
      if (em.attachments && em.attachments.length > 0) {
        attachSection.style.display = "block";
        attachContainer.innerHTML = "";
        em.attachments.forEach((att) => {
          const chip = document.createElement("div");
          chip.className = "gmail-attachment-chip";

          let icon = "fa-file";
          const fn = String(att.name || "").toLowerCase();
          if (fn.endsWith(".pdf")) icon = "fa-file-pdf text-danger";
          else if (fn.endsWith(".xls") || fn.endsWith(".xlsx") || fn.endsWith(".xlsm")) icon = "fa-file-excel text-success";
          else if (fn.endsWith(".doc") || fn.endsWith(".docx")) icon = "fa-file-word text-primary";
          else if (fn.endsWith(".zip") || fn.endsWith(".tar") || fn.endsWith(".gz")) icon = "fa-file-archive text-warning";
          else if (fn.endsWith(".png") || fn.endsWith(".jpg") || fn.endsWith(".jpeg")) icon = "fa-file-image text-info";
          else icon = "fa-file-code text-secondary";

          chip.innerHTML = `
            <div class="gmail-attachment-icon-box">
              <i class="fas ${icon} fs-3"></i>
            </div>
            <div class="gmail-attachment-meta">
              <div class="fw-semibold text-truncate text-body" title="${att.name}">${att.name}</div>
              <div class="text-muted d-flex justify-content-between align-items-center mt-1">
                <span>${att.size || ""}</span>
                <i class="fas fa-arrow-down small"></i>
              </div>
            </div>
          `;
          attachContainer.appendChild(chip);
        });
      } else {
        attachSection.style.display = "none";
      }
    }

    // Sandboxed Gmail document body iframe
    if (bodyEl) {
      bodyEl.innerHTML = "";
      const iframe = document.createElement("iframe");
      iframe.setAttribute("sandbox", "allow-same-origin");
      iframe.className = "w-100 border-0";
      iframe.style.minHeight = "220px";
      iframe.style.background = "transparent";

      const isLight = document.documentElement.getAttribute("data-bs-theme") === "light";
      const bgColor = isLight ? "#ffffff" : "#141a23";
      const textColor = isLight ? "#1e293b" : "#f1f5f9";
      const linkColor = isLight ? "#0284c7" : "#38bdf8";
      const buttonBg = isLight ? "#1a73e8" : "#2563eb";
      const borderColor = isLight ? "#e2e8f0" : "#334155";
      const quoteBg = isLight ? "#f8fafc" : "rgba(56, 189, 248, 0.08)";
      const quoteBorder = isLight ? "#cbd5e1" : "#38bdf8";

      const safeHtml = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; font-src 'self';">
          <style>
            * { box-sizing: border-box; }
            html, body {
              margin: 0;
              padding: 0;
              background-color: ${bgColor};
            }
            body {
              color: ${textColor};
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Google Sans", Helvetica, Arial, sans-serif;
              font-size: 14px;
              line-height: 1.6;
              padding: 16px 20px;
              word-wrap: break-word;
            }
            p { margin: 0 0 12px 0; }
            p:last-child { margin-bottom: 0; }
            a, .inbox-safe-link, [data-real-url] {
              color: ${linkColor};
              text-decoration: underline;
              cursor: pointer;
              word-break: break-all;
              font-weight: 500;
            }
            a:hover, .inbox-safe-link:hover {
              filter: brightness(1.2);
            }
            .btn, .btn-primary, [role="button"], button {
              display: inline-block;
              padding: 9px 18px;
              background-color: ${buttonBg};
              color: #ffffff !important;
              text-decoration: none !important;
              border-radius: 4px;
              font-weight: 500;
              font-size: 13px;
              margin: 8px 0;
              border: none;
              cursor: pointer;
              box-shadow: 0 2px 4px rgba(0,0,0,0.25);
            }
            table {
              border-collapse: collapse;
              width: 100%;
              margin: 12px 0;
            }
            td, th {
              border: 1px solid ${borderColor};
              padding: 8px 10px;
            }
            th {
              background: ${isLight ? '#f1f5f9' : 'rgba(255,255,255,0.05)'};
            }
            blockquote {
              border-left: 3px solid ${quoteBorder};
              background: ${quoteBg};
              margin: 12px 0;
              padding: 8px 12px;
              border-radius: 0 4px 4px 0;
              color: ${textColor};
            }
          </style>
        </head>
        <body>
          ${em.body_html || ""}
        </body>
        </html>
      `;

      iframe.srcdoc = safeHtml;
      iframe.onload = () => {
        try {
          const doc = iframe.contentDocument || iframe.contentWindow.document;
          if (doc && doc.body) {
            iframe.style.height = Math.max(220, doc.body.scrollHeight + 24) + "px";
          }
          const links = doc ? doc.querySelectorAll("a, .inbox-safe-link, [data-real-url]") : [];
          links.forEach((link) => {
            const destUrl = link.getAttribute("data-real-url") || link.getAttribute("href") || "#";
            link.addEventListener("click", (evt) => {
              evt.preventDefault();
              evt.stopPropagation();
              if (urlStatusBar) urlStatusBar.textContent = destUrl;
            });
            link.addEventListener("mouseenter", () => {
              if (urlStatusBar) urlStatusBar.textContent = destUrl;
            });
            link.addEventListener("mouseleave", () => {
              if (urlStatusBar) urlStatusBar.textContent = "Hover over any link in the message to preview destination URL";
            });
          });
        } catch (e) {
          console.warn("Sandboxed iframe inspection restriction:", e);
        }
      };

      bodyEl.appendChild(iframe);
    }

    // Highlight action buttons for this email
    const curAction = userActions[em.id];
    document.querySelectorAll(".inbox-action-btn").forEach((btn) => {
      const act = btn.getAttribute("data-action");
      if (act === curAction) {
        btn.classList.add("active");
        if (act === "report") btn.classList.replace("btn-outline-danger", "btn-danger");
        else if (act === "safe") btn.classList.replace("btn-outline-success", "btn-success");
        else if (act === "delete") btn.classList.replace("btn-outline-secondary", "btn-secondary");
      } else {
        btn.classList.remove("active");
        if (act === "report") btn.classList.replace("btn-danger", "btn-outline-danger");
        else if (act === "safe") btn.classList.replace("btn-success", "btn-outline-success");
        else if (act === "delete") btn.classList.replace("btn-secondary", "btn-outline-secondary");
      }
    });
  }

  // Handle email card selection clicks
  document.querySelectorAll(".gmail-item-row").forEach((card) => {
    if (card.dataset.bound) return;
    card.dataset.bound = "true";
    card.addEventListener("click", () => {
      const eid = card.getAttribute("data-email-id");
      if (eid) renderActiveEmail(eid);
    });
  });

  // Handle classification buttons
  document.querySelectorAll(".inbox-action-btn").forEach((btn) => {
    if (btn.dataset.bound) return;
    btn.dataset.bound = "true";
    btn.addEventListener("click", () => {
      const action = btn.getAttribute("data-action");
      if (!action || !currentEmailId) return;

      userActions[currentEmailId] = action;
      try {
        localStorage.setItem(storageKey, JSON.stringify(userActions));
      } catch (e) {}

      updateListBadges();
      renderActiveEmail(currentEmailId);
    });
  });

  // Handle challenge submit button
  if (submitBtn && !submitBtn.dataset.bound) {
    submitBtn.dataset.bound = "true";
    submitBtn.addEventListener("click", () => {
      if (chalInput) {
        chalInput.value = JSON.stringify(userActions);
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const alpineEl = document.querySelector("[x-data='Challenge']");
      if (alpineEl && alpineEl.__x && alpineEl.__x.$data) {
        alpineEl.__x.$data.submission = chalInput ? chalInput.value : JSON.stringify(userActions);
        alpineEl.__x.$data.submitChallenge();
      }
    });
  }

  // Initialize view
  updateListBadges();
  renderActiveEmail(currentEmailId);
  return true;
}

CTFd._internal.challenge.postRender = initPhishingInbox;
window.addEventListener("ctfd:challenge-rendered", initPhishingInbox);

let inboxRetryCount = 0;
const inboxTimer = setInterval(function() {
  inboxRetryCount++;
  if (initPhishingInbox() || inboxRetryCount > 20) {
    clearInterval(inboxTimer);
  }
}, 50);

CTFd._internal.challenge.submit = function(preview) {
  const challenge_id = parseInt(document.getElementById("challenge-id").value, 10);
  const submission = document.getElementById("challenge-input").value;

  const body = {
    challenge_id: challenge_id,
    submission: submission
  };
  const params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
    return response;
  });
};
