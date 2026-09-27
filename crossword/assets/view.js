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

  const cluesDataEl = document.getElementById("cw-clues-data");
  const solvedCluesEl = document.getElementById("cw-solved-clues-data");
  const cluesContainer = document.getElementById("cw-clues-container");
  const progressBadge = document.getElementById("cw-progress-badge");

  if (!cluesDataEl || !cluesContainer) return;

  let clues = [];
  try {
    clues = JSON.parse(cluesDataEl.value || "[]");
  } catch (e) {
    clues = [];
  }

  let solvedClues = [];
  try {
    solvedClues = JSON.parse(solvedCluesEl ? solvedCluesEl.value : "[]") || [];
  } catch (e) {
    solvedClues = [];
  }

  const storageKey = `ctfd_crossword_answers_${challengeId}`;
  let savedAnswers = {};
  try {
    savedAnswers = JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch (e) {}

  cluesContainer.innerHTML = "";
  if (progressBadge) {
    progressBadge.textContent = `${solvedClues.length} / ${clues.length} Solved`;
  }

  const inputs = {};

  clues.forEach((c) => {
    const isAlreadySolved = solvedClues.includes(c.number);
    const row = document.createElement("div");
    row.className = "d-flex flex-column flex-sm-row justify-content-between align-items-sm-center p-2 mb-2 rounded border border-secondary";
    row.style.background = isAlreadySolved ? "rgba(25, 135, 84, 0.15)" : "rgba(19, 36, 43, 0.7)";

    const infoDiv = document.createElement("div");
    infoDiv.className = "me-2 mb-2 mb-sm-0";
    const statusBadge = isAlreadySolved 
      ? '<span class="badge bg-success me-1">Solved</span>' 
      : `<span class="badge bg-secondary me-1">#${c.number}</span>`;

    infoDiv.innerHTML = `
      ${statusBadge}
      <strong class="text-light">${c.clue}</strong>
      <span class="text-muted small ms-1">(${c.length} letters)</span>
    `;

    const inputDiv = document.createElement("div");
    inputDiv.style.minWidth = "180px";

    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = c.length;
    input.className = "form-control form-control-sm font-monospace text-uppercase";
    input.placeholder = `${c.length} letters`;
    input.value = savedAnswers[c.number] || "";
    if (isAlreadySolved) {
      input.style.borderColor = "#198754";
      input.disabled = true;
    }

    input.addEventListener("input", () => {
      input.value = input.value.toUpperCase();
      savedAnswers[c.number] = input.value;
      localStorage.setItem(storageKey, JSON.stringify(savedAnswers));
      updateProgress();
    });

    input.addEventListener("focus", () => {
      const challengeInput = document.getElementById("challenge-input");
      if (challengeInput && input.value) {
        challengeInput.value = input.value;
      }
    });

    inputDiv.appendChild(input);
    row.appendChild(infoDiv);
    row.appendChild(inputDiv);
    cluesContainer.appendChild(row);

    inputs[c.number] = input;
  });

  function updateProgress() {
    let filled = 0;
    clues.forEach((c) => {
      const val = inputs[c.number] ? inputs[c.number].value : "";
      if (val.length === c.length || solvedClues.includes(c.number)) {
        filled++;
        if (inputs[c.number] && !solvedClues.includes(c.number)) {
          inputs[c.number].style.borderColor = "var(--cyber-cyan, #0dcaf0)";
        }
      }
    });
    if (progressBadge) {
      progressBadge.textContent = `${solvedClues.length > 0 ? solvedClues.length : filled} / ${clues.length} Solved`;
      if (filled === clues.length || solvedClues.length === clues.length) {
        progressBadge.className = "badge bg-success font-monospace";
      } else {
        progressBadge.className = "badge bg-secondary font-monospace";
      }
    }
  }

  updateProgress();
});
