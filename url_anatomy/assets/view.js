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

  const configJsonEl = document.getElementById("url-anatomy-config-json");
  const chalInput = document.getElementById("challenge-input");
  const answeredCountEl = document.getElementById("url-answered-count");
  const submitBtn = document.getElementById("challenge-submit");

  let config = {};
  if (configJsonEl && configJsonEl.textContent) {
    try {
      config = JSON.parse(configJsonEl.textContent);
    } catch (e) {
      console.error("Failed to parse url_anatomy config JSON:", e);
    }
  }

  if (Object.keys(config).length === 0 && CTFd._internal.challenge.data) {
    config = CTFd._internal.challenge.data;
  }

  const urls = config.urls_data || [];
  const isSolved = Boolean(config.is_solved);
  const storageKey = `ctfd_url_anatomy_${challengeId}`;

  let userSelections = {};
  try {
    userSelections = JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch (e) {
    userSelections = {};
  }

  function updateSelectionsUI() {
    let answered = 0;
    urls.forEach((u) => {
      const selected = userSelections[u.id];
      const previewEl = document.querySelector(`.selected-segment-preview[data-url-id="${u.id}"]`);
      const statusBadge = document.querySelector(`.token-status-badge[data-url-id="${u.id}"]`);
      const buttons = document.querySelectorAll(`.url-token-btn[data-url-id="${u.id}"]`);

      if (selected) {
        answered++;
        if (previewEl) previewEl.textContent = selected;
        if (statusBadge) {
          statusBadge.textContent = "SELECTED";
          statusBadge.className = "badge bg-success token-status-badge font-monospace";
        }
      } else {
        if (previewEl) previewEl.textContent = "None";
        if (statusBadge) {
          statusBadge.textContent = "PENDING";
          statusBadge.className = "badge bg-secondary token-status-badge font-monospace";
        }
      }

      buttons.forEach((btn) => {
        const val = btn.getAttribute("data-token-value");
        const puny = btn.getAttribute("data-token-punycode");
        const isMatched = selected && (selected === val || (puny && selected === puny));
        if (isMatched) {
          btn.classList.add("btn-warning", "text-dark", "fw-bold");
          btn.classList.remove("btn-outline-light");
        } else {
          btn.classList.remove("btn-warning", "text-dark", "fw-bold");
          btn.classList.add("btn-outline-light");
        }
      });
    });

    if (answeredCountEl) {
      answeredCountEl.textContent = answered;
    }

    if (chalInput) {
      chalInput.value = JSON.stringify(userSelections);
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (submitBtn) {
      submitBtn.disabled = !(urls.length > 0 && answered >= urls.length);
    }
  }

  // Token click handlers
  document.querySelectorAll(".url-token-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (isSolved) return;
      const urlId = btn.getAttribute("data-url-id");
      const tokenVal = btn.getAttribute("data-token-value");
      if (!urlId || !tokenVal) return;

      userSelections[urlId] = tokenVal;
      try {
        localStorage.setItem(storageKey, JSON.stringify(userSelections));
      } catch (e) {}

      updateSelectionsUI();
    });
  });

  // Punycode toggle handlers
  document.querySelectorAll(".punycode-toggle-btn").forEach((toggleBtn) => {
    let showRaw = false;
    toggleBtn.addEventListener("click", () => {
      showRaw = !showRaw;
      const urlId = toggleBtn.getAttribute("data-url-id");
      toggleBtn.textContent = showRaw ? "Show Unicode (Rendered)" : "Show Punycode (Raw)";

      document.querySelectorAll(`.url-token-btn[data-url-id="${urlId}"]`).forEach((btn) => {
        const puny = btn.getAttribute("data-token-punycode");
        const val = btn.getAttribute("data-token-value");
        const textSpan = btn.querySelector(".token-text");
        if (puny && textSpan) {
          textSpan.textContent = showRaw ? puny : val;
        }
      });
    });
  });

  // Challenge submit button handler
  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      if (chalInput) {
        chalInput.value = JSON.stringify(userSelections);
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const parentSubmit = document.querySelector(".submit-row button#challenge-submit");
      if (parentSubmit && parentSubmit !== submitBtn) {
        parentSubmit.click();
      } else if (window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge) {
        window.CTFd.pages.challenge.submitChallenge(challengeId, JSON.stringify(userSelections));
      }
    });
  }

  updateSelectionsUI();
});
