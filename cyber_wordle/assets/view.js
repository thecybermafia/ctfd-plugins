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

  // Build grid HTML
  const grid = $("#wordle-grid");
  grid.empty();

  for (let r = 0; r < maxAttempts; r++) {
    const rowEl = $('<div class="d-flex justify-content-center gap-1 wordle-row" data-row="' + r + '"></div>');
    const guessData = history[r];

    for (let c = 0; c < wordLen; c++) {
      let letter = "";
      let bgStyle = "background: rgba(15, 23, 42, 0.7);";
      let textStyle = "color: #fff;";

      if (guessData) {
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

      const tile = $(
        '<div class="wordle-tile font-monospace fw-bold d-flex justify-content-center align-items-center rounded fs-4" ' +
        'style="width: 52px; height: 52px; border: 2px solid rgba(255,255,255,0.2); ' + bgStyle + textStyle + '" ' +
        'data-col="' + c + '">' + letter + '</div>'
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

    if (currentWord.length === wordLen) {
      $("#challenge-input").val(currentWord);
      $("#challenge-submit, #wordle-direct-submit").prop("disabled", false);
    } else {
      $("#challenge-input").val("");
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
    $("#challenge-input").val(currentWord);

    const alpineEl = document.querySelector("[x-data='Challenge']");
    if (alpineEl && alpineEl.__x && alpineEl.__x.$data) {
      alpineEl.__x.$data.submission = currentWord;
      alpineEl.__x.$data.submitChallenge();
    } else {
      $("#challenge-submit").click();
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

let wordleRetryCount = 0;
const wordleTimer = setInterval(function() {
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
        if (window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge) {
          const alpineBoard = document.querySelector("[x-data='ChallengeBoard']");
          if (alpineBoard && alpineBoard.__x && alpineBoard.__x.$data) {
            alpineBoard.__x.$data.loadChallenge(challenge_id);
          }
        }
      }, 600);
    }
    return response;
  });
};
