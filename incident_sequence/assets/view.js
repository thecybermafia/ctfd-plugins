CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;
CTFd._internal.challenge.postRender = initIncidentSequence;
window.addEventListener("ctfd:challenge-rendered", initIncidentSequence);

let seqRetryCount = 0;
const seqTimer = setInterval(function() {
  seqRetryCount++;
  if (initIncidentSequence() || seqRetryCount > 20) {
    clearInterval(seqTimer);
  }
}, 50);

CTFd._internal.challenge.submit = function(preview) {
  const challenge_id = parseInt(document.getElementById("challenge-id").value, 10);
  const submission = document.getElementById("challenge-input") ? document.getElementById("challenge-input").value : "";

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

function initIncidentSequence() {
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return;
  const challengeId = chalIdEl.value;

  const container = document.querySelector(`.incident-sequence-container[data-chal-id="${challengeId}"]`);
  if (!container) return;

  // Make modal wider if inside standard CTFd modal
  const col = container.closest(".col-sm-8");
  if (col) {
    col.classList.remove("col-sm-8");
    col.classList.add("col-12");
  }
  const submitRow = container.closest(".submit-row");
  if (submitRow) {
    const keySubmit = submitRow.querySelector(".key-submit");
    if (keySubmit) keySubmit.style.display = "none";
  }

  const configJsonEl = document.getElementById("incident-sequence-config-json");
  const chalInput = document.getElementById("challenge-input");
  const timelineContainer = container.querySelector("#timeline-card-list");
  const distractorContainer = container.querySelector("#distractor-card-list");
  const timelineCountEl = container.querySelector("#seq-timeline-count");
  const distractorCountEl = container.querySelector("#seq-distractor-count");
  const submitBtn = container.querySelector("#challenge-submit");
  const resetBtn = container.querySelector("#seq-reset-btn");
  const feedbackAlert = container.querySelector("#seq-feedback-alert");
  const debriefContainer = container.querySelector("#seq-debrief-container");

  let config = {};
  if (configJsonEl && configJsonEl.textContent) {
    try {
      config = JSON.parse(configJsonEl.textContent);
    } catch (e) {
      console.error("Failed to parse incident_sequence config JSON:", e);
    }
  }

  if (Object.keys(config).length === 0 && CTFd._internal.challenge.data) {
    config = CTFd._internal.challenge.data;
  }

  const allCards = config.cards_data || [];
  const cardsById = {};
  allCards.forEach((c) => {
    cardsById[String(c.id)] = c;
  });

  const allowDistractorBin = Boolean(config.allow_distractor_bin);
  const isSolved = Boolean(config.is_solved);
  const storageKey = `ctfd_incident_seq_${challengeId}`;

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  let timelineList = [];
  let distractorList = [];

  let savedState = null;
  if (!isSolved) {
    try {
      savedState = JSON.parse(localStorage.getItem(storageKey));
    } catch (e) {}
  }

  if (savedState && Array.isArray(savedState.sequence)) {
    timelineList = savedState.sequence.map(String).filter((id) => cardsById[id]);
    distractorList = (savedState.distractors || []).map(String).filter((id) => cardsById[id]);
    // Append any newly added cards that weren't in savedState
    allCards.forEach((c) => {
      const cid = String(c.id);
      if (!timelineList.includes(cid) && !distractorList.includes(cid)) {
        timelineList.push(cid);
      }
    });
  } else {
    // Initial default: all cards in timeline
    timelineList = allCards.map((c) => String(c.id));
    distractorList = [];
  }

  function saveState() {
    if (!isSolved) {
      try {
        localStorage.setItem(
          storageKey,
          JSON.stringify({
            sequence: timelineList,
            distractors: distractorList
          })
        );
      } catch (e) {}
    }

    const payload = JSON.stringify({
      sequence: timelineList,
      distractors: distractorList
    });

    if (chalInput) {
      chalInput.value = payload;
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (timelineCountEl) timelineCountEl.textContent = timelineList.length;
    if (distractorCountEl) distractorCountEl.textContent = distractorList.length;
  }

  // Drag and drop state
  let draggedCardInfo = null;

  function renderCards() {
    if (!timelineContainer) return;
    timelineContainer.innerHTML = "";

    if (timelineList.length === 0) {
      timelineContainer.innerHTML = `
        <div class="p-4 text-center text-muted small border border-dashed border-secondary border-opacity-25 rounded bg-body-tertiary">
          <i class="fas fa-layer-group fa-2x mb-2 opacity-50"></i><br>
          Timeline is empty.<br>Drag cards or click <strong>Timeline</strong> to restore steps here.
        </div>
      `;
    } else {
      timelineList.forEach((cardId, index) => {
        const card = cardsById[cardId];
        if (!card) return;

        const cardEl = document.createElement("div");
        cardEl.className = "card mb-2 p-2 border border-secondary border-opacity-25 shadow-sm seq-card bg-body";
        cardEl.draggable = !isSolved;
        cardEl.setAttribute("data-card-id", cardId);
        cardEl.setAttribute("data-index", index);

        const moveUpDisabled = index === 0 || isSolved ? "disabled" : "";
        const moveDownDisabled = index === timelineList.length - 1 || isSolved ? "disabled" : "";

        let distractorBtn = "";
        if (allowDistractorBin && !isSolved) {
          distractorBtn = `
            <button type="button" class="btn btn-sm btn-outline-danger py-0 px-2 action-to-distractor" title="Move to Prohibited Bin" style="font-size: 0.8rem;">
              <i class="fas fa-ban me-1"></i>Bin
            </button>
          `;
        }

        cardEl.innerHTML = `
          <div class="d-flex justify-content-between align-items-center gap-2">
            <div class="d-flex align-items-center gap-2 flex-grow-1 min-w-0">
              ${!isSolved ? `<span class="seq-handle me-1" title="Drag to reorder"><i class="fas fa-grip-vertical"></i></span>` : ""}
              <span class="badge bg-success text-dark font-monospace flex-shrink-0">#${index + 1}</span>
              <span class="small text-body fw-medium text-wrap text-break">${escapeHtml(card.text)}</span>
            </div>
            <div class="d-flex align-items-center gap-1 flex-shrink-0">
              <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 action-move-up" ${moveUpDisabled} title="Move Up">
                <i class="fas fa-chevron-up"></i>
              </button>
              <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 action-move-down" ${moveDownDisabled} title="Move Down">
                <i class="fas fa-chevron-down"></i>
              </button>
              ${distractorBtn}
            </div>
          </div>
        `;

        if (!isSolved) {
          // Button listeners
          const upBtn = cardEl.querySelector(".action-move-up");
          if (upBtn) {
            upBtn.addEventListener("click", (e) => {
              e.stopPropagation();
              if (index > 0) {
                const temp = timelineList[index];
                timelineList[index] = timelineList[index - 1];
                timelineList[index - 1] = temp;
                saveState();
                renderCards();
              }
            });
          }

          const downBtn = cardEl.querySelector(".action-move-down");
          if (downBtn) {
            downBtn.addEventListener("click", (e) => {
              e.stopPropagation();
              if (index < timelineList.length - 1) {
                const temp = timelineList[index];
                timelineList[index] = timelineList[index + 1];
                timelineList[index + 1] = temp;
                saveState();
                renderCards();
              }
            });
          }

          const binBtn = cardEl.querySelector(".action-to-distractor");
          if (binBtn) {
            binBtn.addEventListener("click", (e) => {
              e.stopPropagation();
              timelineList.splice(index, 1);
              distractorList.push(cardId);
              saveState();
              renderCards();
            });
          }

          // Drag listeners on card
          cardEl.addEventListener("dragstart", (e) => {
            draggedCardInfo = { cardId, from: "timeline", index };
            e.dataTransfer.setData("text/plain", JSON.stringify(draggedCardInfo));
            cardEl.classList.add("seq-dragging");
          });

          cardEl.addEventListener("dragend", () => {
            cardEl.classList.remove("seq-dragging");
            draggedCardInfo = null;
            document.querySelectorAll(".seq-drag-over").forEach((el) => el.classList.remove("seq-drag-over"));
          });

          cardEl.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.stopPropagation();
          });

          cardEl.addEventListener("drop", (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!draggedCardInfo) return;

            const fromCardId = draggedCardInfo.cardId;
            const fromContainer = draggedCardInfo.from;
            const toIndex = index;

            if (fromContainer === "timeline") {
              const oldIdx = timelineList.indexOf(fromCardId);
              if (oldIdx > -1) {
                timelineList.splice(oldIdx, 1);
                timelineList.splice(toIndex, 0, fromCardId);
              }
            } else if (fromContainer === "distractor") {
              const oldIdx = distractorList.indexOf(fromCardId);
              if (oldIdx > -1) {
                distractorList.splice(oldIdx, 1);
                timelineList.splice(toIndex, 0, fromCardId);
              }
            }

            saveState();
            renderCards();
          });
        }

        timelineContainer.appendChild(cardEl);
      });
    }

    // Render distractors
    if (distractorContainer && allowDistractorBin) {
      distractorContainer.innerHTML = "";

      if (distractorList.length === 0) {
        distractorContainer.innerHTML = `
          <div class="p-4 text-center text-muted small border border-dashed border-danger border-opacity-25 rounded bg-body-tertiary">
            <i class="fas fa-trash-can fa-2x mb-2 text-danger opacity-50"></i><br>
            No actions in bin.<br>Drag cards or click <strong>Bin</strong> to isolate prohibited actions here.
          </div>
        `;
      } else {
        distractorList.forEach((cardId, dIndex) => {
          const card = cardsById[cardId];
          if (!card) return;

          const dEl = document.createElement("div");
          dEl.className = "card mb-2 p-2 border border-secondary border-opacity-25 shadow-sm seq-card bg-body";
          dEl.draggable = !isSolved;
          dEl.setAttribute("data-card-id", cardId);
          dEl.setAttribute("data-index", dIndex);

          dEl.innerHTML = `
            <div class="d-flex justify-content-between align-items-center gap-2">
              <div class="d-flex align-items-center gap-2 flex-grow-1 min-w-0">
                ${!isSolved ? `<span class="seq-handle text-danger me-1" title="Drag to restore"><i class="fas fa-grip-vertical"></i></span>` : ""}
                <span class="badge bg-danger text-uppercase font-monospace flex-shrink-0">PROHIBITED</span>
                <span class="small text-body fw-medium text-wrap text-break">${escapeHtml(card.text)}</span>
              </div>
              ${!isSolved ? `
                <div class="flex-shrink-0">
                  <button type="button" class="btn btn-sm btn-outline-success py-0 px-2 action-to-timeline" title="Restore to Timeline" style="font-size: 0.8rem;">
                    <i class="fas fa-arrow-left me-1"></i>Timeline
                  </button>
                </div>
              ` : ""}
            </div>
          `;

          if (!isSolved) {
            const restoreBtn = dEl.querySelector(".action-to-timeline");
            if (restoreBtn) {
              restoreBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                distractorList.splice(dIndex, 1);
                timelineList.push(cardId);
                saveState();
                renderCards();
              });
            }

            dEl.addEventListener("dragstart", (e) => {
              draggedCardInfo = { cardId, from: "distractor", index: dIndex };
              e.dataTransfer.setData("text/plain", JSON.stringify(draggedCardInfo));
              dEl.classList.add("seq-dragging");
            });

            dEl.addEventListener("dragend", () => {
              dEl.classList.remove("seq-dragging");
              draggedCardInfo = null;
              document.querySelectorAll(".seq-drag-over").forEach((el) => el.classList.remove("seq-drag-over"));
            });

            dEl.addEventListener("dragover", (e) => {
              e.preventDefault();
              e.stopPropagation();
            });

            dEl.addEventListener("drop", (e) => {
              e.preventDefault();
              e.stopPropagation();
              if (!draggedCardInfo) return;

              const fromCardId = draggedCardInfo.cardId;
              const fromContainer = draggedCardInfo.from;

              if (fromContainer === "timeline") {
                const oldIdx = timelineList.indexOf(fromCardId);
                if (oldIdx > -1) {
                  timelineList.splice(oldIdx, 1);
                  distractorList.splice(dIndex, 0, fromCardId);
                }
              } else if (fromContainer === "distractor") {
                const oldIdx = distractorList.indexOf(fromCardId);
                if (oldIdx > -1) {
                  distractorList.splice(oldIdx, 1);
                  distractorList.splice(dIndex, 0, fromCardId);
                }
              }

              saveState();
              renderCards();
            });
          }

          distractorContainer.appendChild(dEl);
        });
      }
    }

    saveState();
  }

  // Setup container drop handlers
  if (!isSolved) {
    if (timelineContainer) {
      timelineContainer.addEventListener("dragover", (e) => {
        e.preventDefault();
        timelineContainer.classList.add("seq-drag-over");
      });
      timelineContainer.addEventListener("dragleave", (e) => {
        if (!timelineContainer.contains(e.relatedTarget)) {
          timelineContainer.classList.remove("seq-drag-over");
        }
      });
      timelineContainer.addEventListener("drop", (e) => {
        e.preventDefault();
        timelineContainer.classList.remove("seq-drag-over");
        if (!draggedCardInfo) return;

        const fromCardId = draggedCardInfo.cardId;
        const fromContainer = draggedCardInfo.from;

        if (fromContainer === "distractor") {
          const idx = distractorList.indexOf(fromCardId);
          if (idx > -1) distractorList.splice(idx, 1);
          if (!timelineList.includes(fromCardId)) {
            timelineList.push(fromCardId);
          }
          saveState();
          renderCards();
        }
      });
    }

    if (distractorContainer) {
      distractorContainer.addEventListener("dragover", (e) => {
        e.preventDefault();
        distractorContainer.classList.add("seq-drag-over");
      });
      distractorContainer.addEventListener("dragleave", (e) => {
        if (!distractorContainer.contains(e.relatedTarget)) {
          distractorContainer.classList.remove("seq-drag-over");
        }
      });
      distractorContainer.addEventListener("drop", (e) => {
        e.preventDefault();
        distractorContainer.classList.remove("seq-drag-over");
        if (!draggedCardInfo) return;

        const fromCardId = draggedCardInfo.cardId;
        const fromContainer = draggedCardInfo.from;

        if (fromContainer === "timeline") {
          const idx = timelineList.indexOf(fromCardId);
          if (idx > -1) timelineList.splice(idx, 1);
          if (!distractorList.includes(fromCardId)) {
            distractorList.push(fromCardId);
          }
          saveState();
          renderCards();
        }
      });
    }
  }

  // Reset button
  if (resetBtn && !resetBtn.dataset.bound) {
    resetBtn.dataset.bound = "true";
    resetBtn.addEventListener("click", () => {
      timelineList = allCards.map((c) => String(c.id));
      distractorList = [];
      try {
        localStorage.removeItem(storageKey);
      } catch (e) {}
      saveState();
      renderCards();
      if (feedbackAlert) {
        feedbackAlert.classList.add("d-none");
      }
    });
  }

  // Render debrief dynamically after solve
  function renderLiveDebrief(solveData) {
    if (!debriefContainer) return;
    const steps = solveData.steps_data || config.steps_data || [];
    const distractors = solveData.distractors_data || config.distractors_data || [];
    const explanation = solveData.explanation || config.explanation || "";

    let stepsHtml = "";
    steps.forEach((s, idx) => {
      stepsHtml += `
        <div class="list-group-item bg-transparent border-secondary border-opacity-25 p-2">
          <div class="d-flex align-items-start gap-2">
            <span class="badge bg-success text-dark font-monospace mt-1">#${idx + 1}</span>
            <div>
              <div class="fw-bold font-monospace small text-body">${escapeHtml(s.text || s.title)}</div>
              ${s.explanation ? `<div class="text-muted font-monospace small mt-1">${escapeHtml(s.explanation)}</div>` : ""}
            </div>
          </div>
        </div>
      `;
    });

    let distHtml = "";
    if (distractors.length > 0) {
      distractors.forEach((d) => {
        distHtml += `
          <div class="list-group-item bg-transparent border-danger border-opacity-25 p-2">
            <div class="fw-bold font-monospace text-danger small">${escapeHtml(d.text || d.title)}</div>
            ${d.explanation ? `<div class="text-muted font-monospace small mt-1">${escapeHtml(d.explanation)}</div>` : ""}
          </div>
        `;
      });
    }

    debriefContainer.innerHTML = `
      <div class="card border-success shadow-sm">
        <div class="card-header bg-success bg-opacity-25 text-success fw-bold font-monospace py-2">
          <i class="fas fa-clipboard-check me-2"></i> Standard Operating Procedure (SOP) Debrief
        </div>
        <div class="card-body">
          ${explanation ? `<div class="mb-3 small font-monospace text-body">${escapeHtml(explanation)}</div>` : ""}
          <div class="mb-2 font-monospace fw-bold text-success small">
            <i class="fas fa-check-circle me-1"></i> Verified Playbook Steps:
          </div>
          <div class="list-group list-group-flush mb-3">
            ${stepsHtml}
          </div>
          ${distHtml ? `
            <div class="mb-2 font-monospace fw-bold text-danger small">
              <i class="fas fa-ban me-1"></i> Prohibited Countermeasures:
            </div>
            <div class="list-group list-group-flush">
              ${distHtml}
            </div>
          ` : ""}
        </div>
      </div>
    `;
    debriefContainer.classList.remove("d-none");
  }

  // Submission handler
  if (submitBtn && !submitBtn.dataset.bound) {
    submitBtn.dataset.bound = "true";
    submitBtn.addEventListener("click", async () => {
      if (timelineList.length === 0) {
        if (feedbackAlert) {
          feedbackAlert.className = "alert alert-warning my-2 text-center font-monospace border border-warning";
          feedbackAlert.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i> <strong>Timeline cannot be empty. Arrange steps before submitting.</strong>`;
          feedbackAlert.classList.remove("d-none");
        }
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Verifying Playbook Sequence...';

      const payload = {
        challenge_id: parseInt(challengeId),
        submission: JSON.stringify({
          sequence: timelineList,
          distractors: distractorList
        })
      };

      try {
        const response = await fetch("/api/v1/challenges/attempt", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "CSRF-Token": (window.init && window.init.csrfNonce) || ""
          },
          body: JSON.stringify(payload)
        });

        const res = await response.json();
        const data = res.data || {};
        const status = data.status;
        const message = data.message;

        if (status === "correct") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-success my-2 text-center font-monospace border border-success";
            feedbackAlert.innerHTML = `<i class="fas fa-check-circle me-2"></i> <strong>${message || "Incident Response Playbook Sequence Verified!"}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }

          submitBtn.className = "challenge-submit btn btn-success w-100 py-2 fw-bold font-monospace text-uppercase";
          submitBtn.innerHTML = '<i class="fas fa-check-double me-2"></i> Playbook Verified!';
          submitBtn.disabled = true;

          if (window.WorldAudio && typeof window.WorldAudio.playSolve === "function") {
            window.WorldAudio.playSolve();
          }
          if (typeof window.confetti === "function") {
            window.confetti();
          }

          try {
            localStorage.removeItem(storageKey);
          } catch (e) {}

          // Fetch full challenge details to reveal debrief if needed
          try {
            const detailRes = await fetch(`/api/v1/challenges/${challengeId}`);
            const detailJson = await detailRes.json();
            if (detailJson.data) {
              renderLiveDebrief(detailJson.data);
            }
          } catch (e) {}

          // Sync with Alpine challenge modal
          const chalModal = container ? container.closest("[x-data]") : document.querySelector('[x-data="Challenge"]');
          if (chalModal && window.Alpine && window.Alpine.$data) {
            try {
              const alpineData = window.Alpine.$data(chalModal);
              if (alpineData) {
                alpineData.response = res;
                alpineData.submission = "";
                if (typeof alpineData.renderSubmissionResponse === "function") {
                  alpineData.renderSubmissionResponse();
                }
              }
            } catch (e) {}
          }

          setTimeout(() => {
            window.location.reload();
          }, 1500);

        } else if (status === "already_solved") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-info my-2 text-center font-monospace border border-info";
            feedbackAlert.innerHTML = `<i class="fas fa-info-circle me-2"></i> <strong>${message || "You have already solved this challenge."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          submitBtn.disabled = true;
          setTimeout(() => {
            window.location.reload();
          }, 1200);

        } else if (status === "incorrect") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-danger my-2 text-center font-monospace border border-danger";
            feedbackAlert.innerHTML = `<i class="fas fa-circle-xmark me-2"></i> <strong>${message || "Incorrect playbook sequence. Check dependencies and prohibited actions."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }

          if (window.WorldAudio && typeof window.WorldAudio.playError === "function") {
            window.WorldAudio.playError();
          }

          // Sync with Alpine so attempts counter increments
          const chalModal = container ? container.closest("[x-data]") : document.querySelector('[x-data="Challenge"]');
          if (chalModal && window.Alpine && window.Alpine.$data) {
            try {
              const alpineData = window.Alpine.$data(chalModal);
              if (alpineData) {
                alpineData.response = res;
                if (typeof alpineData.renderSubmissionResponse === "function") {
                  alpineData.renderSubmissionResponse();
                }
              }
            } catch (e) {}
          }

          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i> Submit Playbook Sequence';

        } else if (status === "ratelimited") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-warning my-2 text-center font-monospace border border-warning";
            feedbackAlert.innerHTML = `<i class="fas fa-stopwatch me-2"></i> <strong>${message || "You are submitting too fast. Please wait a few seconds and try again."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          let countdown = 3;
          submitBtn.disabled = true;
          submitBtn.innerHTML = `<i class="fas fa-stopwatch me-2"></i> Wait ${countdown}s...`;
          const timer = setInterval(() => {
            countdown--;
            if (countdown > 0) {
              submitBtn.innerHTML = `<i class="fas fa-stopwatch me-2"></i> Wait ${countdown}s...`;
            } else {
              clearInterval(timer);
              submitBtn.disabled = false;
              submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i> Submit Playbook Sequence';
            }
          }, 1000);

        } else {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-warning my-2 text-center font-monospace border border-warning";
            feedbackAlert.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i> <strong>${message || "Unexpected response. Please try again."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i> Submit Playbook Sequence';
        }

      } catch (err) {
        console.error("IncidentSequence submission failed:", err);
        if (feedbackAlert) {
          feedbackAlert.className = "alert alert-danger my-2 text-center font-monospace border border-danger";
          feedbackAlert.innerHTML = `<i class="fas fa-circle-xmark me-2"></i> <strong>Network error submitting sequence. Please try again.</strong>`;
          feedbackAlert.classList.remove("d-none");
        }
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i> Submit Playbook Sequence';
      }
    });
  }

  renderCards();
}

CTFd.plugin.run((_CTFd) => {
  setTimeout(initIncidentSequence, 50);
});
