CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;
CTFd._internal.challenge.postRender = function() {};
CTFd._internal.challenge.submit = function() {
  return Promise.resolve();
};

CTFd.plugin.run((_CTFd) => {
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return;
  const challengeId = chalIdEl.value;

  const emailsJsonEl = document.getElementById("inbox-emails-json");
  const chalInput = document.getElementById("challenge-input");
  const reviewedCountEl = document.getElementById("inbox-reviewed-count");
  const submitBtn = document.getElementById("challenge-submit");
  const urlStatusBar = document.getElementById("url-status-bar");
  const toggleHeadersBtn = document.getElementById("toggle-headers-btn");
  const headersPanel = document.getElementById("email-headers-panel");

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

  if (!emails || emails.length === 0) return;

  const storageKey = `ctfd_phishing_inbox_${challengeId}`;
  let userActions = {};
  try {
    userActions = JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch (e) {
    userActions = {};
  }

  let currentEmailId = emails[0].id;

  // Toggle headers panel
  if (toggleHeadersBtn && headersPanel) {
    toggleHeadersBtn.addEventListener("click", () => {
      const isVisible = headersPanel.style.display !== "none";
      headersPanel.style.display = isVisible ? "none" : "block";
      toggleHeadersBtn.classList.toggle("active", !isVisible);
    });
  }

  function getStatusLabel(action) {
    switch (action) {
      case "report":
        return { label: "REPORTED", badgeClass: "bg-danger" };
      case "safe":
        return { label: "SAFE", badgeClass: "bg-success" };
      case "delete":
        return { label: "DELETED", badgeClass: "bg-secondary" };
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

    // Sync to hidden input
    if (chalInput) {
      chalInput.value = JSON.stringify(userActions);
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    // Check if submit can be enabled
    if (submitBtn) {
      const allDone = emails.length > 0 && reviewed >= emails.length;
      submitBtn.disabled = !allDone;
    }
  }

  function renderActiveEmail(emailId) {
    const em = emails.find((e) => e.id === emailId) || emails[0];
    if (!em) return;
    currentEmailId = em.id;

    // Update list selection
    document.querySelectorAll(".inbox-item-card").forEach((card) => {
      const isCur = card.getAttribute("data-email-id") === em.id;
      card.classList.toggle("active", isCur);
      card.style.borderLeft = isCur ? "3px solid var(--bs-primary, #0d6efd)" : "3px solid transparent";
    });

    // Populate header info
    const subjEl = document.getElementById("active-email-subject");
    const senderEl = document.getElementById("active-email-sender");
    const senderAddrEl = document.getElementById("active-email-sender-addr");
    const replyToEl = document.getElementById("active-email-reply-to");
    const authBadgesContainer = document.getElementById("active-email-auth-badges");
    const attachSection = document.getElementById("active-email-attachments");
    const attachContainer = document.getElementById("attachments-container");
    const bodyEl = document.getElementById("active-email-body-content");

    if (subjEl) subjEl.textContent = em.subject || "No Subject";
    if (senderEl) senderEl.textContent = em.sender_name || em.sender_email;
    if (senderAddrEl) senderAddrEl.textContent = em.sender_email || "unknown@domain.com";
    if (replyToEl) replyToEl.textContent = em.reply_to || em.sender_email || "None";

    // Auth badges
    if (authBadgesContainer) {
      authBadgesContainer.innerHTML = "";
      if (em.auth_results) {
        Object.entries(em.auth_results).forEach(([proto, status]) => {
          const st = String(status).toUpperCase();
          const badge = document.createElement("span");
          badge.className = `badge ${st === "PASS" ? "bg-success" : "bg-danger"} font-monospace`;
          badge.textContent = `${proto.toUpperCase()}: ${st}`;
          authBadgesContainer.appendChild(badge);
        });
      }
    }

    // Attachments
    if (attachSection && attachContainer) {
      if (em.attachments && em.attachments.length > 0) {
        attachSection.style.display = "block";
        attachContainer.innerHTML = "";
        em.attachments.forEach((att) => {
          const card = document.createElement("div");
          card.className = "p-2 rounded border border-secondary border-opacity-50 font-monospace small d-flex align-items-center gap-2";
          card.style.background = "rgba(0, 0, 0, 0.4)";
          card.innerHTML = `
            <span class="badge bg-warning text-dark">${(att.type || "FILE").toUpperCase()}</span>
            <span class="text-light">${att.name}</span>
            <span class="text-muted small">(${att.size || "Unknown size"})</span>
          `;
          attachContainer.appendChild(card);
        });
      } else {
        attachSection.style.display = "none";
      }
    }

    // Body content & link inspector
    if (bodyEl) {
      bodyEl.innerHTML = em.body_html || "";

      // Attach safe link inspection
      const links = bodyEl.querySelectorAll("a, .inbox-safe-link, [data-real-url]");
      links.forEach((link) => {
        const destUrl = link.getAttribute("data-real-url") || link.getAttribute("href") || "#";

        link.addEventListener("click", (evt) => {
          evt.preventDefault();
          evt.stopPropagation();
          if (urlStatusBar) {
            urlStatusBar.textContent = destUrl;
          }
        });

        link.addEventListener("mouseenter", () => {
          if (urlStatusBar) {
            urlStatusBar.textContent = destUrl;
          }
        });

        link.addEventListener("mouseleave", () => {
          if (urlStatusBar) {
            urlStatusBar.textContent = "Hover over any link to inspect true destination";
          }
        });
      });
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
  document.querySelectorAll(".inbox-item-card").forEach((card) => {
    card.addEventListener("click", () => {
      const eid = card.getAttribute("data-email-id");
      if (eid) renderActiveEmail(eid);
    });
  });

  // Handle classification buttons
  document.querySelectorAll(".inbox-action-btn").forEach((btn) => {
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
  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      if (chalInput) {
        chalInput.value = JSON.stringify(userActions);
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const parentSubmit = document.querySelector(".submit-row button#challenge-submit");
      if (parentSubmit && parentSubmit !== submitBtn) {
        parentSubmit.click();
      } else if (window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge) {
        window.CTFd.pages.challenge.submitChallenge(challengeId, JSON.stringify(userActions));
      }
    });
  }

  // Initialize
  updateListBadges();
  renderActiveEmail(currentEmailId);
});
