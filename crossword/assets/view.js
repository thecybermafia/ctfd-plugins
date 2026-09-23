CTFd.plugin.run((_CTFd) => {
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return;
  const challengeId = chalIdEl.value;

  const cluesDataEl = document.getElementById("cw-clues-data");
  const cluesContainer = document.getElementById("cw-clues-container");
  const progressBadge = document.getElementById("cw-progress-badge");

  if (!cluesDataEl || !cluesContainer) return;

  let clues = [];
  try {
    clues = JSON.parse(cluesDataEl.value || "[]");
  } catch (e) {
    console.error("Failed to parse crossword clues:", e);
  }

  const storageKey = `ctfd_crossword_answers_${challengeId}`;
  let savedAnswers = {};
  try {
    savedAnswers = JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch (e) {}

  cluesContainer.innerHTML = "";
  if (progressBadge) {
    progressBadge.textContent = `0 / ${clues.length} Filled`;
  }

  const inputs = {};

  clues.forEach((c) => {
    const row = document.createElement("div");
    row.className = "d-flex flex-column flex-sm-row justify-content-between align-items-sm-center p-2 mb-2 rounded border border-secondary";
    row.style.background = "rgba(19, 36, 43, 0.7)";

    const infoDiv = document.createElement("div");
    infoDiv.className = "me-2 mb-2 mb-sm-0";
    infoDiv.innerHTML = `
      <span class="badge bg-secondary me-1">#${c.number}</span>
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

    input.addEventListener("input", () => {
      input.value = input.value.toUpperCase();
      savedAnswers[c.number] = input.value;
      localStorage.setItem(storageKey, JSON.stringify(savedAnswers));
      updateProgress();
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
      if (val.length === c.length) {
        filled++;
        inputs[c.number].style.borderColor = "var(--fb-cyan-glow)";
      } else {
        inputs[c.number].style.borderColor = "";
      }
    });
    if (progressBadge) {
      progressBadge.textContent = `${filled} / ${clues.length} Filled`;
      if (filled === clues.length) {
        progressBadge.className = "badge bg-success";
      } else {
        progressBadge.className = "badge bg-secondary";
      }
    }
  }

  updateProgress();
});
