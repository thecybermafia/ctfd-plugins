CTFd.plugin.run((_CTFd) => {
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return;
  const challengeId = chalIdEl.value;

  const sizeEl = document.getElementById("bingo-size");
  const cellsDataEl = document.getElementById("bingo-cells-data");
  const boardGrid = document.getElementById("bingo-board-grid");
  const tilesRatio = document.getElementById("bingo-tiles-ratio");
  const linesCount = document.getElementById("bingo-lines-count");

  const promptBox = document.getElementById("bingo-tile-prompt-box");
  const promptTitle = document.getElementById("bingo-prompt-title");
  const promptPts = document.getElementById("bingo-prompt-pts");
  const promptDesc = document.getElementById("bingo-prompt-desc");
  const promptForm = document.getElementById("bingo-prompt-form");
  const flagInput = document.getElementById("bingo-prompt-flag-input");
  const submitBtn = document.getElementById("bingo-prompt-submit-btn");
  const solvedMsg = document.getElementById("bingo-prompt-solved-msg");

  if (!boardGrid || !cellsDataEl) return;

  const N = parseInt(sizeEl ? sizeEl.value : 5) || 5;
  let cells = [];
  try {
    cells = JSON.parse(cellsDataEl.value || "[]");
  } catch (e) {
    console.error("Failed to parse bingo cells:", e);
  }

  // Ensure 25 cells exist
  const totalCells = N * N;
  while (cells.length < totalCells) {
    const idx = cells.length;
    cells.push({ index: idx, title: `Tile #${idx + 1}`, desc: "No description provided", points: 10 });
  }

  boardGrid.style.gridTemplateColumns = `repeat(${N}, 1fr)`;
  boardGrid.style.maxWidth = `${N * 125}px`;

  let solvedCellsSet = new Set();
  let selectedCellIndex = null;
  const tileElements = {};

  // Build grid
  boardGrid.innerHTML = "";
  cells.forEach((cell, i) => {
    const tile = document.createElement("div");
    tile.className = "bingo-tile";
    tile.dataset.index = i;

    tile.innerHTML = `
      <div class="tile-title">${cell.title}</div>
      <div class="tile-footer">
        <span class="text-muted">#${i + 1}</span>
        <span class="badge ${cell.points > 0 ? 'bg-secondary' : 'bg-dark'}">${cell.points}P</span>
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

    document.querySelectorAll(".bingo-tile.selected").forEach(el => el.classList.remove("selected"));
    if (tileElements[index]) {
      tileElements[index].classList.add("selected");
    }

    promptBox.classList.remove("d-none");
    promptTitle.textContent = `#${index + 1}: ${cell.title}`;
    promptPts.textContent = `${cell.points} PTS`;
    promptDesc.textContent = cell.desc || "Complete this objective and submit the flag below.";

    const isSolved = solvedCellsSet.has(index);
    if (isSolved) {
      promptForm.classList.add("d-none");
      solvedMsg.classList.remove("d-none");
    } else {
      promptForm.classList.remove("d-none");
      solvedMsg.classList.add("d-none");
      flagInput.value = "";
      flagInput.focus();
    }
  }

  function fetchState() {
    fetch(`/api/v1/challenges/${challengeId}/bingo/state`)
      .then(r => r.json())
      .then(res => {
        if (!res.success || !res.data) return;
        solvedCellsSet = new Set(res.data.solved_cells || []);
        
        // Update tiles
        cells.forEach((_, i) => {
          if (tileElements[i]) {
            if (solvedCellsSet.has(i)) {
              tileElements[i].classList.add("solved");
              const footer = tileElements[i].querySelector(".tile-footer");
              if (footer && !footer.querySelector(".fa-check")) {
                footer.innerHTML = `<span class="text-warning"><i class="fas fa-check"></i></span> <span class="badge bg-warning text-dark">DONE</span>`;
              }
            } else {
              tileElements[i].classList.remove("solved");
            }
          }
        });

        // Update stats
        if (tilesRatio) {
          tilesRatio.textContent = `${solvedCellsSet.size} / ${totalCells}`;
        }
        if (linesCount) {
          linesCount.textContent = (res.data.completed_lines || []).length;
        }

        // Refresh active prompt if selected
        if (selectedCellIndex !== null) {
          selectTile(selectedCellIndex);
        }
      })
      .catch(e => console.log("Bingo state error:", e));
  }

  fetchState();

  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      if (selectedCellIndex === null) return;
      const flag = flagInput.value.trim();
      if (!flag) {
        alert("Please enter a flag for this tile.");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';

      fetch(`/api/v1/challenges/${challengeId}/bingo/attempt_cell`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "CSRF-Token": init.csrfNonce
        },
        body: JSON.stringify({
          cell_index: selectedCellIndex,
          flag: flag
        })
      })
        .then(r => r.json())
        .then(res => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-check"></i> Submit Tile';

          if (res.success && res.status === "correct") {
            alert(res.message);
            fetchState();
            // Trigger score/challenge refresh event
            window.dispatchEvent(new CustomEvent("load-challenges"));
          } else {
            alert(res.message || "Incorrect flag for this tile.");
          }
        })
        .catch(err => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-check"></i> Submit Tile';
          alert("Error: " + err);
        });
    });
  }
});
