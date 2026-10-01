(function() {
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

function initBingo() {
  const chalIdEl = document.getElementById("challenge-id");
  const boardGrid = document.getElementById("bingo-board-grid");
  const headerRow = document.getElementById("bingo-header-row");
  const cellsDataEl = document.getElementById("bingo-cells-data");

  if (!chalIdEl || !boardGrid || !cellsDataEl) return false;
  const challengeId = chalIdEl.value;

  if (window.WorldChallengeResizer && typeof window.WorldChallengeResizer.init === "function") {
    window.WorldChallengeResizer.init();
  }

  const sizeEl = document.getElementById("bingo-size");
  const tilesRatio = document.getElementById("bingo-tiles-ratio");
  const linesCount = document.getElementById("bingo-lines-count");

  const promptBadge = document.getElementById("bingo-prompt-badge");
  const promptTitle = document.getElementById("bingo-prompt-title");
  const promptPts = document.getElementById("bingo-prompt-pts");
  const promptDesc = document.getElementById("bingo-prompt-desc");
  const promptForm = document.getElementById("bingo-prompt-form");
  const flagInput = document.getElementById("bingo-prompt-flag-input");
  const submitBtn = document.getElementById("bingo-prompt-submit-btn");
  const solvedMsg = document.getElementById("bingo-prompt-solved-msg");

  const rowsCountEl = document.getElementById("hud-rows-count");
  const colsCountEl = document.getElementById("hud-cols-count");
  const diagsCountEl = document.getElementById("hud-diags-count");

  const N = parseInt(sizeEl ? sizeEl.value : 5, 10) || 5;
  const letters = ["B", "I", "N", "G", "O", "S", "E", "C"];

  let cells = [];
  try {
    cells = JSON.parse(cellsDataEl.value || cellsDataEl.textContent || "[]");
  } catch (e) {
    console.error("Failed to parse bingo cells:", e);
  }

  // Ensure total cells exist
  const totalCells = N * N;
  while (cells.length < totalCells) {
    const idx = cells.length;
    cells.push({ index: idx, title: `Sector #${idx + 1}`, desc: "Authenticate objective flag to neutralize this sector.", points: 10 });
  }

  boardGrid.style.gridTemplateColumns = `repeat(${N}, 1fr)`;

  // Build classic B-I-N-G-O tactical channel modules
  if (headerRow) {
    headerRow.innerHTML = "";
    headerRow.style.gridTemplateColumns = `repeat(${N}, 1fr)`;
    for (let c = 0; c < N; c++) {
      const colLetter = letters[c % letters.length];
      const colEl = document.createElement("div");
      colEl.className = `hud-channel-box hud-chan-${c % 5}`;
      colEl.dataset.col = c;
      colEl.innerHTML = `
        <span class="hud-channel-letter">${colLetter}</span>
        <span class="hud-channel-sub">CHAN ${c + 1}</span>
      `;
      headerRow.appendChild(colEl);
    }
  }

  let solvedCellsSet = new Set();
  let selectedCellIndex = null;
  const tileElements = {};

  // Build tactical grid tiles
  boardGrid.innerHTML = "";
  cells.forEach((cell, i) => {
    const r = Math.floor(i / N);
    const c = i % N;
    const colLetter = letters[c % letters.length];
    const callout = `${colLetter}-${i + 1}`;
    const isCenter = (N % 2 === 1) && (i === Math.floor(totalCells / 2));

    const tile = document.createElement("div");
    tile.className = `hud-tile ${isCenter ? 'center-pivot' : ''}`;
    tile.dataset.index = i;
    tile.dataset.col = c;
    tile.dataset.row = r;

    tile.innerHTML = `
      <div class="hud-tile-header">
        <span class="fw-bold">[ ${callout} ]</span>
        <span class="badge ${cell.points > 0 ? 'bg-secondary' : 'bg-dark'} font-monospace" style="font-size: 0.58rem;">+${cell.points}P</span>
      </div>
      <div class="hud-tile-title" title="${cell.title}">
        ${isCenter ? '<div class="text-warning font-monospace fw-bold mb-0.5" style="font-size: 0.58rem;"><i class="fas fa-crosshairs"></i> FREE PIVOT</div>' : ''}
        <span>${cell.title}</span>
      </div>
    `;

    tile.addEventListener("click", () => {
      selectTile(i);
    });

    boardGrid.appendChild(tile);
    tileElements[i] = tile;
  });

  function selectTile(index) {
    selectedCellIndex = index;
    const cell = cells[index];
    if (!cell) return;

    const r = Math.floor(index / N);
    const c = index % N;
    const colLetter = letters[c % letters.length];
    const callout = `${colLetter}-${index + 1}`;

    document.querySelectorAll(".hud-tile.selected").forEach(el => el.classList.remove("selected"));
    if (tileElements[index]) {
      tileElements[index].classList.add("selected");
    }

    if (promptBadge) {
      promptBadge.textContent = `SECTOR ${callout}`;
      promptBadge.className = `badge font-monospace hud-chan-${c % 5}`;
    }
    if (promptTitle) {
      promptTitle.textContent = cell.title;
    }
    if (promptPts) {
      promptPts.textContent = `+${cell.points} PTS`;
    }
    if (promptDesc) {
      promptDesc.textContent = cell.desc || "Review the objective scenario and authenticate the flag below.";
    }

    const isSolved = solvedCellsSet.has(index);
    if (isSolved) {
      if (promptForm) promptForm.classList.add("d-none");
      if (solvedMsg) {
        solvedMsg.classList.remove("d-none");
        solvedMsg.classList.add("d-flex");
      }
    } else {
      if (promptForm) promptForm.classList.remove("d-none");
      if (solvedMsg) {
        solvedMsg.classList.add("d-none");
        solvedMsg.classList.remove("d-flex");
      }
      if (flagInput) {
        flagInput.value = "";
        flagInput.focus();
      }
    }
  }

  function fetchState() {
    fetch(`/api/v1/challenges/${challengeId}/bingo/state`)
      .then(r => r.json())
      .then(res => {
        if (!res.success || !res.data) return;
        solvedCellsSet = new Set(res.data.solved_cells || []);
        const completedLines = res.data.completed_lines || [];

        let numRows = 0;
        let numCols = 0;
        let numDiags = 0;

        // Track winning line cells
        const winningLineCells = new Set();
        completedLines.forEach(lineId => {
          if (lineId.startsWith("row_")) {
            numRows++;
            const r = parseInt(lineId.replace("row_", ""), 10);
            for (let c = 0; c < N; c++) winningLineCells.add(r * N + c);
          } else if (lineId.startsWith("col_")) {
            numCols++;
            const c = parseInt(lineId.replace("col_", ""), 10);
            for (let r = 0; r < N; r++) winningLineCells.add(r * N + c);
            const colHeader = document.querySelector(`.hud-channel-box[data-col="${c}"]`);
            if (colHeader) colHeader.classList.add("col-completed");
          } else if (lineId === "diag_main") {
            numDiags++;
            for (let i = 0; i < N; i++) winningLineCells.add(i * N + i);
          } else if (lineId === "diag_anti") {
            numDiags++;
            for (let i = 0; i < N; i++) winningLineCells.add(i * N + (N - 1 - i));
          }
        });

        // Update each tile
        cells.forEach((_, i) => {
          const tile = tileElements[i];
          if (!tile) return;

          if (solvedCellsSet.has(i)) {
            tile.classList.add("solved");
            if (!tile.querySelector(".hud-lock-seal")) {
              const stamp = document.createElement("div");
              stamp.className = "hud-lock-seal";
              stamp.innerHTML = `
                <div class="hud-lock-check"><i class="fas fa-shield-alt"></i></div>
                <div class="hud-lock-text">SECURED</div>
              `;
              tile.appendChild(stamp);
            }
          } else {
            tile.classList.remove("solved");
            const existingStamp = tile.querySelector(".hud-lock-seal");
            if (existingStamp) existingStamp.remove();
          }

          if (winningLineCells.has(i)) {
            tile.classList.add("hud-vector-locked");
          } else {
            tile.classList.remove("hud-vector-locked");
          }
        });

        // Update HUD stats
        if (tilesRatio) {
          tilesRatio.textContent = `${solvedCellsSet.size} / ${totalCells}`;
        }
        if (linesCount) {
          linesCount.textContent = completedLines.length;
        }

        // Telemetry breakdown
        if (rowsCountEl) rowsCountEl.textContent = `${numRows} / ${N}`;
        if (colsCountEl) colsCountEl.textContent = `${numCols} / ${N}`;
        if (diagsCountEl) diagsCountEl.textContent = `${numDiags} / 2`;

        // Refresh active prompt
        if (selectedCellIndex !== null) {
          selectTile(selectedCellIndex);
        }
      })
      .catch(e => console.log("Bingo state error:", e));
  }

  // Hook submit button
  if (submitBtn && !submitBtn.dataset.bound) {
    submitBtn.dataset.bound = "true";
    submitBtn.addEventListener("click", () => {
      if (selectedCellIndex === null) return;
      const flag = flagInput ? flagInput.value.trim() : "";
      if (!flag) {
        alert("Please enter a flag or keyword to authenticate this sector.");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> AUTHENTICATING...';

      const csrfToken = (window.init && window.init.csrfNonce) || (window.CTFd && window.CTFd.config && window.CTFd.config.csrfNonce) || "";

      fetch(`/api/v1/challenges/${challengeId}/bingo/attempt_cell`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "CSRF-Token": csrfToken
        },
        body: JSON.stringify({
          cell_index: selectedCellIndex,
          flag: flag
        })
      })
        .then(r => r.json())
        .then(res => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-bolt me-1"></i> AUTHENTICATE &amp; DAUB';

          if (res.success && res.status === "correct") {
            fetchState();
            window.dispatchEvent(new CustomEvent("load-challenges"));
          } else {
            alert(res.message || "Incorrect flag or answer for this sector.");
          }
        })
        .catch(err => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-bolt me-1"></i> AUTHENTICATE &amp; DAUB';
          alert("Error: " + err);
        });
    });
  }

  if (flagInput && !flagInput.dataset.bound) {
    flagInput.dataset.bound = "true";
    flagInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (submitBtn) submitBtn.click();
      }
    });
  }

  // Prime sector 0 on load so the console is immediately active
  selectTile(0);
  fetchState();
  return true;
}

CTFd._internal.challenge.postRender = initBingo;
window.addEventListener("ctfd:challenge-rendered", initBingo);

var bingoRetryCount = 0;
var bingoTimer = setInterval(function() {
  bingoRetryCount++;
  if (initBingo() || bingoRetryCount > 20) {
    clearInterval(bingoTimer);
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
})();
