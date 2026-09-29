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

  const configJsonEl = document.getElementById("incident-sequence-config-json");
  const chalInput = document.getElementById("challenge-input");
  const timelineContainer = document.getElementById("timeline-card-list");
  const distractorContainer = document.getElementById("distractor-card-list");
  const timelineCountEl = document.getElementById("timeline-cards-count");
  const distractorCountEl = document.getElementById("distractor-cards-count");
  const submitBtn = document.getElementById("challenge-submit");

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
    cardsById[c.id] = c;
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
  try {
    savedState = JSON.parse(localStorage.getItem(storageKey));
  } catch (e) {}

  if (savedState && Array.isArray(savedState.sequence)) {
    timelineList = savedState.sequence.filter((id) => cardsById[id]);
    distractorList = (savedState.distractors || []).filter((id) => cardsById[id]);
    // Append any newly added cards that weren't in savedState
    allCards.forEach((c) => {
      if (!timelineList.includes(c.id) && !distractorList.includes(c.id)) {
        timelineList.push(c.id);
      }
    });
  } else {
    // Initial default: all cards in timeline
    timelineList = allCards.map((c) => c.id);
    distractorList = [];
  }

  function saveState() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        sequence: timelineList,
        distractors: distractorList
      }));
    } catch (e) {}

    if (chalInput) {
      chalInput.value = JSON.stringify({
        sequence: timelineList,
        distractors: distractorList
      });
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (timelineCountEl) timelineCountEl.textContent = timelineList.length;
    if (distractorCountEl) distractorCountEl.textContent = distractorList.length;
  }

  function renderCards() {
    if (!timelineContainer) return;
    timelineContainer.innerHTML = "";

    timelineList.forEach((cardId, index) => {
      const card = cardsById[cardId];
      if (!card) return;

      const cardEl = document.createElement("div");
      cardEl.className = "card mb-2 p-2 border border-secondary border-opacity-50 text-light";
      cardEl.style.background = "rgba(10, 20, 30, 0.85)";
      cardEl.style.cursor = isSolved ? "default" : "grab";
      cardEl.draggable = !isSolved;
      cardEl.setAttribute("data-card-id", cardId);

      const moveUpDisabled = index === 0 || isSolved ? "disabled" : "";
      const moveDownDisabled = index === timelineList.length - 1 || isSolved ? "disabled" : "";

      let distractorBtn = "";
      if (allowDistractorBin && !isSolved) {
        distractorBtn = `
          <button type="button" class="btn btn-sm btn-outline-danger py-0 px-2 font-monospace action-to-distractor" title="Move to Prohibited Bin" style="font-size: 0.75rem;">
            Bin &rarr;
          </button>
        `;
      }

      cardEl.innerHTML = `
        <div class="d-flex justify-content-between align-items-center gap-2">
          <div class="d-flex align-items-center gap-2 flex-grow-1">
            <span class="badge bg-success font-monospace">#${index + 1}</span>
            <span class="font-monospace small text-light text-wrap">${escapeHtml(card.text)}</span>
          </div>
          <div class="d-flex align-items-center gap-1 flex-shrink-0">
            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-1 font-monospace action-move-up" ${moveUpDisabled} title="Move Up">
              &uarr;
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-1 font-monospace action-move-down" ${moveDownDisabled} title="Move Down">
              &darr;
            </button>
            ${distractorBtn}
          </div>
        </div>
      `;

      // Button listeners
      if (!isSolved) {
        const upBtn = cardEl.querySelector(".action-move-up");
        if (upBtn) {
          upBtn.addEventListener("click", () => {
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
          downBtn.addEventListener("click", () => {
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
          binBtn.addEventListener("click", () => {
            timelineList.splice(index, 1);
            distractorList.push(cardId);
            saveState();
            renderCards();
          });
        }

        // HTML5 drag and drop
        cardEl.addEventListener("dragstart", (e) => {
          e.dataTransfer.setData("text/plain", JSON.stringify({ cardId, from: "timeline", index }));
          cardEl.style.opacity = "0.4";
        });
        cardEl.addEventListener("dragend", () => {
          cardEl.style.opacity = "1";
        });
      }

      timelineContainer.appendChild(cardEl);
    });

    // Render distractors
    if (distractorContainer && allowDistractorBin) {
      distractorContainer.innerHTML = "";

      if (distractorList.length === 0) {
        distractorContainer.innerHTML = `
          <div class="p-3 text-center text-muted font-monospace small border border-dashed border-danger border-opacity-25 rounded">
            Drop or move prohibited / false-lead actions here.
          </div>
        `;
      } else {
        distractorList.forEach((cardId, dIndex) => {
          const card = cardsById[cardId];
          if (!card) return;

          const dEl = document.createElement("div");
          dEl.className = "card mb-2 p-2 border border-danger border-opacity-50 text-light";
          dEl.style.background = "rgba(40, 10, 10, 0.85)";
          dEl.style.cursor = isSolved ? "default" : "grab";
          dEl.draggable = !isSolved;
          dEl.setAttribute("data-card-id", cardId);

          dEl.innerHTML = `
            <div class="d-flex justify-content-between align-items-center gap-2">
              <div class="d-flex align-items-center gap-2 flex-grow-1">
                <span class="badge bg-danger font-monospace">PROHIBITED</span>
                <span class="font-monospace small text-light text-wrap">${escapeHtml(card.text)}</span>
              </div>
              ${!isSolved ? `
                <button type="button" class="btn btn-sm btn-outline-success py-0 px-2 font-monospace action-to-timeline" title="Restore to Timeline" style="font-size: 0.75rem;">
                  &larr; Timeline
                </button>
              ` : ""}
            </div>
          `;

          if (!isSolved) {
            const restoreBtn = dEl.querySelector(".action-to-timeline");
            if (restoreBtn) {
              restoreBtn.addEventListener("click", () => {
                distractorList.splice(dIndex, 1);
                timelineList.push(cardId);
                saveState();
                renderCards();
              });
            }

            dEl.addEventListener("dragstart", (e) => {
              e.dataTransfer.setData("text/plain", JSON.stringify({ cardId, from: "distractor", index: dIndex }));
              dEl.style.opacity = "0.4";
            });
            dEl.addEventListener("dragend", () => {
              dEl.style.opacity = "1";
            });
          }

          distractorContainer.appendChild(dEl);
        });
      }
    }

    saveState();
  }

  // Setup drop containers
  if (!isSolved) {
    if (timelineContainer) {
      timelineContainer.addEventListener("dragover", (e) => e.preventDefault());
      timelineContainer.addEventListener("drop", (e) => {
        e.preventDefault();
        try {
          const data = JSON.parse(e.dataTransfer.getData("text/plain"));
          if (data && data.cardId) {
            if (data.from === "distractor") {
              const idx = distractorList.indexOf(data.cardId);
              if (idx > -1) distractorList.splice(idx, 1);
              timelineList.push(data.cardId);
              saveState();
              renderCards();
            }
          }
        } catch (err) {}
      });
    }

    if (distractorContainer) {
      distractorContainer.addEventListener("dragover", (e) => e.preventDefault());
      distractorContainer.addEventListener("drop", (e) => {
        e.preventDefault();
        try {
          const data = JSON.parse(e.dataTransfer.getData("text/plain"));
          if (data && data.cardId) {
            if (data.from === "timeline") {
              const idx = timelineList.indexOf(data.cardId);
              if (idx > -1) timelineList.splice(idx, 1);
              distractorList.push(data.cardId);
              saveState();
              renderCards();
            }
          }
        } catch (err) {}
      });
    }
  }

  // Challenge submit button handler
  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      const payload = JSON.stringify({
        sequence: timelineList,
        distractors: distractorList
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

  renderCards();
});
