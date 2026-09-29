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

  const configJsonEl = document.getElementById("branching-scenario-config-json");
  const chalInput = document.getElementById("challenge-input");
  const restartBtn = document.getElementById("scenario-restart-btn");
  const statusBadge = document.getElementById("scenario-status-badge");
  const titleEl = document.getElementById("scenario-node-title");
  const badgeEl = document.getElementById("scenario-node-badge");
  const textEl = document.getElementById("scenario-node-text");
  const consequenceBox = document.getElementById("scenario-consequence-box");
  const consequenceText = document.getElementById("scenario-consequence-text");
  const mediaContainer = document.getElementById("scenario-media-container");
  const mediaElement = document.getElementById("scenario-media-element");
  const transcriptBox = document.getElementById("scenario-transcript-box");
  const transcriptText = document.getElementById("scenario-transcript-text");
  const actionsSection = document.getElementById("scenario-actions-section");
  const optionsContainer = document.getElementById("scenario-options-container");
  const outcomeCard = document.getElementById("scenario-outcome-card");
  const outcomeTitle = document.getElementById("scenario-outcome-title");
  const outcomeDesc = document.getElementById("scenario-outcome-desc");
  const outcomeActions = document.getElementById("scenario-outcome-actions");
  const submitBtn = document.getElementById("challenge-submit");

  let config = {};
  if (configJsonEl && configJsonEl.textContent) {
    try {
      config = JSON.parse(configJsonEl.textContent);
    } catch (e) {
      console.error("Failed to parse branching_scenario config JSON:", e);
    }
  }

  if (Object.keys(config).length === 0 && CTFd._internal.challenge.data) {
    config = CTFd._internal.challenge.data;
  }

  const nodes = config.nodes_data || {};
  const startNodeId = config.start_node_id || "start";
  const winningNodes = (config.winning_nodes || "win").split(",").map((s) => s.trim().toLowerCase());
  const showFeedback = config.show_feedback !== false;
  const isSolved = Boolean(config.is_solved);
  const storageKey = `ctfd_scenario_state_${challengeId}`;

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  let currentNodeId = startNodeId;
  let historyPath = [startNodeId];
  let lastConsequence = "";

  // Load saved state
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved && saved.currentNodeId && nodes[saved.currentNodeId]) {
      currentNodeId = saved.currentNodeId;
      historyPath = saved.historyPath || [currentNodeId];
      lastConsequence = saved.lastConsequence || "";
    }
  } catch (e) {}

  function saveState() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        currentNodeId,
        historyPath,
        lastConsequence
      }));
    } catch (e) {}

    if (chalInput) {
      chalInput.value = JSON.stringify({
        node_id: currentNodeId,
        path: historyPath
      });
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  function restartScenario() {
    currentNodeId = startNodeId;
    historyPath = [startNodeId];
    lastConsequence = "";
    saveState();
    renderNode(currentNodeId);
  }

  if (restartBtn) {
    restartBtn.addEventListener("click", restartScenario);
  }

  function renderNode(nodeId) {
    const node = nodes[nodeId];
    if (!node) {
      if (titleEl) titleEl.textContent = "Error: Incident State Undefined";
      if (textEl) textEl.textContent = `Node '${nodeId}' not found in scenario configuration.`;
      return;
    }

    currentNodeId = nodeId;

    // Title and step badge
    if (titleEl) titleEl.textContent = node.title || `Incident Decision`;
    if (badgeEl) badgeEl.textContent = `STEP ${historyPath.length}`;

    // Consequence feedback
    if (consequenceBox && consequenceText) {
      if (showFeedback && lastConsequence) {
        consequenceBox.style.display = "block";
        consequenceText.textContent = lastConsequence;
      } else {
        consequenceBox.style.display = "none";
      }
    }

    // Multimedia container
    if (mediaContainer && mediaElement) {
      let hasMedia = false;
      mediaElement.innerHTML = "";

      if (node.media_url) {
        hasMedia = true;
        if (node.media_type === "audio") {
          mediaElement.innerHTML = `
            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="badge bg-danger font-monospace">AUDIO INTERCEPT</span>
              <audio controls class="w-100 mt-1" src="${node.media_url}"></audio>
            </div>
          `;
        } else {
          mediaElement.innerHTML = `
            <img src="${node.media_url}" alt="Incident Evidence" class="img-fluid rounded mb-2" style="max-height: 280px;">
          `;
        }
      }

      if (node.transcript && transcriptBox && transcriptText) {
        hasMedia = true;
        transcriptBox.style.display = "block";
        transcriptText.textContent = node.transcript;
      } else if (transcriptBox) {
        transcriptBox.style.display = "none";
      }

      mediaContainer.style.display = hasMedia ? "block" : "none";
    }

    // Main narrative text
    if (textEl) {
      textEl.textContent = node.text || "";
    }

    const isWin = winningNodes.includes(nodeId.toLowerCase()) || node.is_win;
    const isEnding = node.is_ending || isWin || !node.options || node.options.length === 0;

    if (isEnding) {
      // Ending reached
      if (actionsSection) actionsSection.style.display = "none";
      if (outcomeCard) outcomeCard.style.display = "block";

      if (isWin) {
        if (statusBadge) {
          statusBadge.textContent = "RESOLVED";
          statusBadge.className = "badge bg-success font-monospace";
        }
        if (outcomeCard) {
          outcomeCard.className = "p-3 rounded border border-success text-center font-monospace mt-3 bg-dark";
          outcomeCard.style.boxShadow = "0 0 15px rgba(40, 167, 69, 0.4)";
        }
        if (outcomeTitle) {
          outcomeTitle.textContent = "CRISIS CONTAINED - OBJECTIVE ACCOMPLISHED";
          outcomeTitle.className = "h5 fw-bold mb-2 text-success";
        }
        if (outcomeDesc) {
          outcomeDesc.textContent = node.text || "You successfully neutralized the deceptive threat and followed incident response protocol.";
        }
        if (outcomeActions) outcomeActions.innerHTML = "";
        if (submitBtn) {
          submitBtn.style.display = "block";
          submitBtn.disabled = false;
        }
      } else {
        if (statusBadge) {
          statusBadge.textContent = "COMPROMISED";
          statusBadge.className = "badge bg-danger font-monospace";
        }
        if (outcomeCard) {
          outcomeCard.className = "p-3 rounded border border-danger text-center font-monospace mt-3 bg-dark";
        }
        if (outcomeTitle) {
          outcomeTitle.textContent = "BREACH OCCURRED - COUNTERMEASURE FAILED";
          outcomeTitle.className = "h5 fw-bold mb-2 text-danger";
        }
        if (outcomeDesc) {
          outcomeDesc.textContent = node.text || "The attack succeeded. Review standard procedures and select safer countermeasures.";
        }
        if (outcomeActions) {
          outcomeActions.innerHTML = `
            <button type="button" class="btn btn-outline-warning font-monospace py-1 px-3 btn-sm restart-outcome-btn">
              Restart Incident
            </button>
          `;
          outcomeActions.querySelector(".restart-outcome-btn").addEventListener("click", restartScenario);
        }
        if (submitBtn) submitBtn.style.display = "none";
      }
    } else {
      // Intermediate state: render action options
      if (statusBadge) {
        statusBadge.textContent = "ACTIVE";
        statusBadge.className = "badge bg-info font-monospace";
      }
      if (outcomeCard) outcomeCard.style.display = "none";
      if (actionsSection) actionsSection.style.display = "block";
      if (submitBtn) submitBtn.style.display = "none";

      if (optionsContainer) {
        optionsContainer.innerHTML = "";
        (node.options || []).forEach((opt, idx) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn btn-outline-light text-start p-2 font-monospace d-flex align-items-center gap-2";
          btn.style.background = "rgba(0, 0, 0, 0.4)";
          btn.style.borderColor = "rgba(255, 255, 255, 0.2)";
          btn.innerHTML = `
            <span class="badge bg-secondary font-monospace" style="font-size: 0.7rem;">#${idx + 1}</span>
            <span class="small text-light flex-grow-1">${escapeHtml(opt.text)}</span>
            <span class="text-muted small">&rarr;</span>
          `;

          btn.addEventListener("click", () => {
            if (isSolved) return;
            lastConsequence = opt.consequence || "";
            if (opt.next_node) {
              historyPath.push(opt.next_node);
              renderNode(opt.next_node);
              saveState();
            }
          });

          optionsContainer.appendChild(btn);
        });
      }
    }

    saveState();
  }

  // Challenge submit button handler
  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      const payload = JSON.stringify({
        node_id: currentNodeId,
        path: historyPath
      });
      if (chalInput) {
        chalInput.value = payload;
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const parentSubmit = document.querySelector(".submit-row button#challenge-submit");
      if (parentSubmit && parentSubmit !== submitBtn) {
        parentSubmit.click();
      } else if (window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge) {
        window.CTFd.pages.challenge.submitChallenge(challengeId, payload);
      }
    });
  }

  renderNode(currentNodeId);
});
