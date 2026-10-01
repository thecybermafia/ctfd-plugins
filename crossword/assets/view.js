(function() {
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

function initCrossword() {
  const chalIdEl = document.getElementById("challenge-id");
  const cluesDataEl = document.getElementById("cw-clues-data");
  const gridCellsArea = document.getElementById("cw-grid-cells-area");
  const cluesContainer = document.getElementById("cw-clues-container");
  const progressBadge = document.getElementById("cw-progress-badge");

  if (!chalIdEl || !cluesDataEl || !gridCellsArea || !cluesContainer) return false;
  const challengeId = chalIdEl.value;

  let clues = [];
  try {
    clues = JSON.parse(cluesDataEl.value || cluesDataEl.textContent || "[]");
  } catch (e) {
    console.error("Failed to parse crossword clues:", e);
  }

  if (!clues || clues.length === 0) {
    if (CTFd._internal.challenge.data && CTFd._internal.challenge.data.clues_data) {
      clues = CTFd._internal.challenge.data.clues_data;
    }
  }

  const storageKey = `ctfd_crossword_answers_${challengeId}`;
  let savedAnswers = {};
  try {
    savedAnswers = JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch (e) {}

  gridCellsArea.innerHTML = "";
  cluesContainer.innerHTML = "";

  const cellInputMatrix = {}; // clueNum -> [input0, input1, ...]
  const clueItemElements = {}; // clueNum -> element

  // 1. Build Interactive Crossword Puzzle Board
  clues.forEach((c) => {
    cellInputMatrix[c.number] = [];
    const wordRow = document.createElement("div");
    wordRow.className = "cw-grid-row d-flex flex-wrap align-items-center gap-2 p-2 rounded";
    wordRow.dataset.clueNum = c.number;

    // Row Label / Number
    const rowLabel = document.createElement("div");
    rowLabel.className = "d-flex align-items-center gap-1 font-monospace fw-bold";
    rowLabel.style.minWidth = "65px";
    rowLabel.innerHTML = `<span class="badge bg-secondary">#${c.number}</span>`;

    // Row Letter Cells Container
    const cellsContainer = document.createElement("div");
    cellsContainer.className = "d-flex align-items-center gap-1";

    const savedWord = (savedAnswers[c.number] || "").padEnd(c.length, " ");

    for (let i = 0; i < c.length; i++) {
      const cellBox = document.createElement("div");
      cellBox.className = "cw-cell-box";

      if (i === 0) {
        const sub = document.createElement("span");
        sub.className = "cw-cell-sub";
        sub.textContent = c.number;
        cellBox.appendChild(sub);
      }

      const input = document.createElement("input");
      input.type = "text";
      input.maxLength = 1;
      input.className = "cw-cell-input font-monospace fw-bold text-center text-uppercase";
      input.dataset.clue = c.number;
      input.dataset.idx = i;
      input.autocomplete = "off";

      const initChar = savedWord[i] && savedWord[i] !== " " ? savedWord[i] : "";
      input.value = initChar;

      // Realtime Typing Navigation
      input.addEventListener("input", () => {
        input.value = input.value.toUpperCase();
        syncWordFromCells(c.number);
        if (input.value && i < c.length - 1) {
          cellInputMatrix[c.number][i + 1]?.focus();
        }
      });

      input.addEventListener("keydown", (e) => {
        if (e.key === "Backspace") {
          if (!input.value && i > 0) {
            e.preventDefault();
            const prev = cellInputMatrix[c.number][i - 1];
            if (prev) {
              prev.value = "";
              prev.focus();
              syncWordFromCells(c.number);
            }
          } else {
            setTimeout(() => syncWordFromCells(c.number), 10);
          }
        } else if (e.key === "ArrowRight" && i < c.length - 1) {
          e.preventDefault();
          cellInputMatrix[c.number][i + 1]?.focus();
        } else if (e.key === "ArrowLeft" && i > 0) {
          e.preventDefault();
          cellInputMatrix[c.number][i - 1]?.focus();
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          const nextClue = clues.find(x => x.number > c.number);
          if (nextClue && cellInputMatrix[nextClue.number]) {
            const targetIdx = Math.min(i, nextClue.length - 1);
            cellInputMatrix[nextClue.number][targetIdx]?.focus();
          }
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          const prevClues = clues.filter(x => x.number < c.number);
          if (prevClues.length > 0) {
            const prevClue = prevClues[prevClues.length - 1];
            if (cellInputMatrix[prevClue.number]) {
              const targetIdx = Math.min(i, prevClue.length - 1);
              cellInputMatrix[prevClue.number][targetIdx]?.focus();
            }
          }
        }
      });

      input.addEventListener("focus", () => {
        highlightActiveClue(c.number);
      });

      cellBox.appendChild(input);
      cellsContainer.appendChild(cellBox);
      cellInputMatrix[c.number].push(input);
    }

    // Clue quick preview pill
    const previewPill = document.createElement("div");
    previewPill.className = "d-none d-md-inline-block small text-muted font-monospace text-truncate ms-2";
    previewPill.style.maxWidth = "280px";
    previewPill.title = c.clue;
    previewPill.innerHTML = `<i class="fas fa-arrow-left me-1"></i> <span class="fst-italic">${c.clue}</span>`;

    wordRow.appendChild(rowLabel);
    wordRow.appendChild(cellsContainer);
    wordRow.appendChild(previewPill);
    gridCellsArea.appendChild(wordRow);
  });

  // 2. Build Clues List
  clues.forEach((c) => {
    const clueCard = document.createElement("div");
    clueCard.className = "cw-clue-item d-flex justify-content-between align-items-center p-2 px-3 mb-2 rounded border";
    clueCard.style.background = "var(--matrix-bg-card, rgba(19, 36, 43, 0.7))";
    clueCard.style.borderColor = "var(--matrix-border, rgba(255, 255, 255, 0.15))";
    clueCard.dataset.clueNum = c.number;

    clueCard.innerHTML = `
      <div class="d-flex align-items-center gap-2">
        <span class="badge bg-secondary font-monospace">#${c.number}</span>
        <strong class="text-light small font-monospace">${c.clue}</strong>
      </div>
      <div class="d-flex align-items-center gap-2">
        <span class="badge bg-dark border border-secondary text-muted font-monospace small">${c.length} letters</span>
        <span class="cw-clue-status badge bg-secondary font-monospace" style="font-size: 0.7rem;">INCOMPLETE</span>
      </div>
    `;

    clueCard.addEventListener("click", () => {
      highlightActiveClue(c.number);
      cellInputMatrix[c.number]?.[0]?.focus();
    });

    cluesContainer.appendChild(clueCard);
    clueItemElements[c.number] = clueCard;
  });

  function highlightActiveClue(clueNum) {
    document.querySelectorAll(".cw-clue-item").forEach(el => el.classList.remove("active-clue"));
    if (clueItemElements[clueNum]) {
      clueItemElements[clueNum].classList.add("active-clue");
    }
  }

  function syncWordFromCells(clueNum) {
    const inputs = cellInputMatrix[clueNum];
    if (!inputs) return;
    const word = inputs.map(inp => inp.value || " ").join("").trimEnd();
    savedAnswers[clueNum] = word;
    try {
      localStorage.setItem(storageKey, JSON.stringify(savedAnswers));
    } catch (e) {}

    updateWordStatus(clueNum);
    updateProgress();
  }

  function updateWordStatus(clueNum) {
    const clue = clues.find(x => x.number === clueNum);
    if (!clue) return;
    const inputs = cellInputMatrix[clueNum];
    const fullWord = inputs.map(inp => inp.value).join("");
    const isFull = fullWord.length === clue.length && !fullWord.includes(" ");

    const row = document.querySelector(`.cw-grid-row[data-clue-num="${clueNum}"]`);
    if (row) {
      row.classList.toggle("word-solved", isFull);
    }

    const clueCard = clueItemElements[clueNum];
    if (clueCard) {
      const statusBadge = clueCard.querySelector(".cw-clue-status");
      if (statusBadge) {
        if (isFull) {
          statusBadge.textContent = fullWord;
          statusBadge.className = "cw-clue-status badge bg-success text-dark font-monospace fw-bold";
        } else {
          statusBadge.textContent = "INCOMPLETE";
          statusBadge.className = "cw-clue-status badge bg-secondary font-monospace";
        }
      }
    }
  }

  function updateProgress() {
    let filled = 0;
    clues.forEach((c) => {
      const inputs = cellInputMatrix[c.number];
      const fullWord = inputs ? inputs.map(inp => inp.value).join("") : "";
      if (fullWord.length === c.length && !fullWord.includes(" ")) {
        filled++;
      }
    });

    if (progressBadge) {
      progressBadge.textContent = `${filled} / ${clues.length} Solved`;
      if (filled === clues.length) {
        progressBadge.className = "badge bg-success text-dark font-monospace fw-bold";
      } else {
        progressBadge.className = "badge bg-secondary font-monospace";
      }
    }
  }

  // Initial status calculation for loaded answers
  clues.forEach((c) => {
    updateWordStatus(c.number);
  });
  updateProgress();

  // Hook submit button
  const submitBtn = document.getElementById("challenge-submit");
  const chalInput = document.getElementById("challenge-input");
  if (submitBtn && !submitBtn.dataset.cwBound) {
    submitBtn.dataset.cwBound = "true";
    submitBtn.addEventListener("click", () => {
      const val = chalInput ? chalInput.value : "";
      const alpineEl = document.querySelector("[x-data='Challenge']");
      if (alpineEl && alpineEl.__x && alpineEl.__x.$data) {
        alpineEl.__x.$data.submission = val;
        alpineEl.__x.$data.submitChallenge();
      }
    });
  }

  if (chalInput && !chalInput.dataset.cwBound) {
    chalInput.dataset.cwBound = "true";
    chalInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (submitBtn) submitBtn.click();
      }
    });
  }

  updateProgress();
  return true;
}

CTFd._internal.challenge.postRender = initCrossword;
window.addEventListener("ctfd:challenge-rendered", initCrossword);

var cwRetryCount = 0;
var cwTimer = setInterval(function() {
  cwRetryCount++;
  if (initCrossword() || cwRetryCount > 20) {
    clearInterval(cwTimer);
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
})();
