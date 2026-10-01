(function() {
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

function initWordle() {
  const $ = (window.CTFd && window.CTFd.lib && window.CTFd.lib.$) || window.$;
  if (!$) return false;

  const container = $("#wordle-container");
  if (!container.length) return false;

  const wordLen = parseInt(container.attr("data-word-len") || "5", 10);
  const maxAttempts = parseInt(container.attr("data-max-attempts") || "6", 10);
  let isSolved = container.attr("data-solved") === "true";

  let history = [];
  try {
    const raw = $("#wordle-history-json").text();
    history = JSON.parse(raw || "[]");
  } catch (e) {
    history = [];
  }

  let currentAttempt = history.length;
  let currentWord = "";
  const keyStatus = {}; // letter -> 'correct' | 'present' | 'absent'

  // Build grid HTML: ONLY render completed rows and the active row.
  // Rows after the active row are strictly omitted from the DOM to prevent inspection/tampering.
  const grid = $("#wordle-grid");
  grid.empty();

  const rowsToRender = (isSolved || currentAttempt >= maxAttempts)
    ? Math.min(history.length, maxAttempts)
    : Math.min(history.length + 1, maxAttempts);

  for (let r = 0; r < rowsToRender; r++) {
    const isCompleted = r < history.length;
    const isActive = (r === currentAttempt && !isSolved && currentAttempt < maxAttempts);
    const guessData = history[r];

    const rowEl = $(
      '<div class="d-flex justify-content-center gap-1 wordle-row ' +
      (isActive ? 'wordle-row-active' : 'wordle-row-completed') +
      '"' + (isActive ? ' data-row="' + r + '"' : '') + '></div>'
    );

    for (let c = 0; c < wordLen; c++) {
      let letter = "";
      let bgStyle = "background: rgba(15, 23, 42, 0.7);";
      let textStyle = "color: #fff;";
      let borderStyle = "border: 2px solid rgba(255,255,255,0.2);";

      if (isCompleted && guessData) {
        letter = guessData.word[c] || "";
        const evalStatus = (guessData.evaluation && guessData.evaluation[c]) || "absent";
        if (evalStatus === "correct") {
          bgStyle = "background: var(--matrix-green, #198754);";
          textStyle = "color: #030d06; font-weight: 800;";
          keyStatus[letter] = "correct";
        } else if (evalStatus === "present") {
          bgStyle = "background: #d97706;";
          textStyle = "color: #fff;";
          if (keyStatus[letter] !== "correct") keyStatus[letter] = "present";
        } else {
          bgStyle = "background: #374151;";
          textStyle = "color: #9ca3af;";
          if (!keyStatus[letter]) keyStatus[letter] = "absent";
        }
      }

      const colAttr = isActive ? ' data-col="' + c + '"' : '';
      const tile = $(
        '<div class="wordle-tile font-monospace fw-bold d-flex justify-content-center align-items-center rounded fs-4" ' +
        'style="width: 52px; height: 52px; ' + borderStyle + ' ' + bgStyle + textStyle + '"' +
        colAttr + '>' + letter + '</div>'
      );
      rowEl.append(tile);
    }
    grid.append(rowEl);
  }

  // Build Keyboard HTML
  const keyboardRows = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
    ["ENTER", "Z", "X", "C", "V", "B", "N", "M", "DEL"]
  ];

  function renderKeyboard() {
    const kb = $("#wordle-keyboard");
    kb.empty();

    keyboardRows.forEach(function(row) {
      const rowDiv = $('<div class="d-flex justify-content-center gap-1 w-100"></div>');
      row.forEach(function(key) {
        let bg = "background: #1e293b;";
        let color = "#e2e8f0;";
        const st = keyStatus[key];
        if (st === "correct") {
          bg = "background: var(--matrix-green, #198754);";
          color = "#030d06;";
        } else if (st === "present") {
          bg = "background: #d97706;";
          color = "#fff;";
        } else if (st === "absent") {
          bg = "background: #334155;";
          color = "#64748b;";
        }

        const isAction = key === "ENTER" || key === "DEL";
        const flexStyle = isAction ? "flex: 1.5; font-size: 0.8rem;" : "flex: 1; font-size: 1rem;";

        const btn = $(
          '<button type="button" class="btn p-0 font-monospace fw-bold rounded d-flex justify-content-center align-items-center wordle-key" ' +
          'style="height: 48px; border: 1px solid rgba(255,255,255,0.1); ' + bg + ' color: ' + color + ' ' + flexStyle + '" ' +
          'data-key="' + key + '">' + key + '</button>'
        );
        rowDiv.append(btn);
      });
      kb.append(rowDiv);
    });
  }

  renderKeyboard();

  function updateActiveRow() {
    if (isSolved || currentAttempt >= maxAttempts) {
      $("#challenge-submit, #wordle-direct-submit").prop("disabled", true);
      return;
    }

    const row = grid.find('.wordle-row[data-row="' + currentAttempt + '"]');
    for (let c = 0; c < wordLen; c++) {
      const tile = row.find('.wordle-tile[data-col="' + c + '"]');
      const letter = currentWord[c] || "";
      tile.text(letter);
      if (letter) {
        tile.css({
          "border-color": "var(--matrix-green, #00ff41)",
          "background": "var(--matrix-green-subtle, rgba(0, 255, 65, 0.15))",
          "box-shadow": "0 0 8px var(--matrix-green-glow)"
        });
      } else {
        tile.css({
          "border-color": "rgba(255,255,255,0.2)",
          "background": "rgba(15, 23, 42, 0.7)",
          "box-shadow": "none"
        });
      }
    }

    const chalInput = document.getElementById("challenge-input");
    if (currentWord.length === wordLen) {
      if (chalInput) {
        chalInput.value = currentWord;
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      $("#challenge-submit, #wordle-direct-submit").prop("disabled", false);
    } else {
      if (chalInput) {
        chalInput.value = "";
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      $("#challenge-submit, #wordle-direct-submit").prop("disabled", true);
    }

    // Sync input box value if not currently focused
    const typeInput = $("#wordle-type-input");
    if (typeInput.length && !typeInput.is(":focus") && typeInput.val() !== currentWord) {
      typeInput.val(currentWord);
    }
  }

  function handleKeyInput(key) {
    if (isSolved || currentAttempt >= maxAttempts) return;
    key = (key || "").toUpperCase();

    if (key === "BACKSPACE" || key === "DEL") {
      if (currentWord.length > 0) {
        currentWord = currentWord.slice(0, -1);
        updateActiveRow();
      }
    } else if (key === "ENTER") {
      if (currentWord.length === wordLen) {
        triggerSubmit();
      }
    } else if (/^[A-Z]$/.test(key)) {
      if (currentWord.length < wordLen) {
        currentWord += key;
        updateActiveRow();
      }
    }
  }

  function triggerSubmit() {
    if (currentWord.length !== wordLen) return;
    const chalInput = document.getElementById("challenge-input");
    if (chalInput) {
      chalInput.value = currentWord;
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    const alpineEl = document.querySelector("[x-data='Challenge']");
    let alpineData = null;
    if (window.Alpine && typeof window.Alpine.$data === "function" && alpineEl) {
      alpineData = window.Alpine.$data(alpineEl);
    } else if (alpineEl && alpineEl._x_dataStack) {
      alpineData = alpineEl._x_dataStack[0];
    } else if (alpineEl && alpineEl.__x) {
      alpineData = alpineEl.__x.$data;
    }

    if (alpineData && typeof alpineData.submitChallenge === "function") {
      alpineData.submission = currentWord;
      alpineData.submitChallenge();
    } else {
      const submitBtn = document.getElementById("challenge-submit");
      if (submitBtn) submitBtn.click();
    }
  }

  // Bind physical input field
  $(document).off("input", "#wordle-type-input").on("input", "#wordle-type-input", function() {
    let val = ($(this).val() || "").toUpperCase().replace(/[^A-Z]/g, "");
    if (val.length > wordLen) val = val.slice(0, wordLen);
    $(this).val(val);
    currentWord = val;
    updateActiveRow();
  });

  $(document).off("keydown", "#wordle-type-input").on("keydown", "#wordle-type-input", function(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      triggerSubmit();
    }
  });

  $(document).off("click", "#wordle-direct-submit").on("click", "#wordle-direct-submit", function() {
    triggerSubmit();
  });

  // Bind virtual keyboard clicks
  $(document).off("click", ".wordle-key").on("click", ".wordle-key", function(e) {
    e.preventDefault();
    const key = $(this).attr("data-key");
    handleKeyInput(key);
  });

  // Bind physical keyboard on document when not in other input
  $(document).off("keydown.wordle").on("keydown.wordle", function(e) {
    if ($(e.target).is("input, textarea")) return;
    if (e.key === "Backspace") {
      handleKeyInput("DEL");
    } else if (e.key === "Enter") {
      handleKeyInput("ENTER");
    } else if (e.key && e.key.length === 1 && /^[a-zA-Z]$/.test(e.key)) {
      handleKeyInput(e.key.toUpperCase());
    }
  });

  $(document).off("click", "#challenge-submit").on("click", "#challenge-submit", function() {
    triggerSubmit();
  });

  updateActiveRow();
  return true;
}

CTFd._internal.challenge.postRender = initWordle;
window.addEventListener("ctfd:challenge-rendered", initWordle);

var wordleRetryCount = 0;
var wordleTimer = setInterval(function() {
  wordleRetryCount++;
  if (initWordle() || wordleRetryCount > 20) {
    clearInterval(wordleTimer);
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
    if (response && response.data) {
      // Reload challenge modal view after attempt to refresh wordle grid and keyboard state
      setTimeout(function() {
        const alpineBoard = document.querySelector("[x-data='ChallengeBoard']");
        let boardData = null;
        if (window.Alpine && typeof window.Alpine.$data === "function" && alpineBoard) {
          boardData = window.Alpine.$data(alpineBoard);
        } else if (alpineBoard && alpineBoard._x_dataStack) {
          boardData = alpineBoard._x_dataStack[0];
        } else if (alpineBoard && alpineBoard.__x) {
          boardData = alpineBoard.__x.$data;
        }

        if (boardData && typeof boardData.loadChallenge === "function") {
          boardData.loadChallenge(challenge_id);
        }
      }, 500);
    }
    return response;
  });
};
})();
