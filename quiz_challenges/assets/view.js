(function() {
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

function initQuiz() {
  const $ = (window.CTFd && window.CTFd.lib && window.CTFd.lib.$) || window.$;
  if (!$) return false;

  const container = $(".quiz-challenge-container");
  if (!container.length) return false;

  function updateQuizSelection() {
    const selected = [];
    $(".quiz-option-input:checked").each(function() {
      selected.push($(this).val());
    });

    // Highlight selected card labels
    $(".quiz-option-label").each(function() {
      const input = $(this).find(".quiz-option-input");
      if (input.is(":checked")) {
        $(this).css({
          "border-color": "var(--matrix-green, #00ff41)",
          "background": "var(--matrix-green-subtle, rgba(0, 255, 65, 0.12))",
          "box-shadow": "0 0 8px var(--matrix-green-glow, rgba(0, 255, 65, 0.25))"
        });
      } else {
        $(this).css({
          "border-color": "var(--matrix-border, rgba(255, 255, 255, 0.15))",
          "background": "var(--matrix-bg-card, rgba(15, 23, 42, 0.7))",
          "box-shadow": "none"
        });
      }
    });

    const chalInput = document.getElementById("challenge-input");
    if (selected.length > 0) {
      if (chalInput) {
        chalInput.value = selected.join(",");
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      $("#challenge-submit").prop("disabled", false);
    } else {
      if (chalInput) {
        chalInput.value = "";
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      $("#challenge-submit").prop("disabled", true);
    }
  }

  $(document).off("change", ".quiz-option-input").on("change", ".quiz-option-input", function() {
    updateQuizSelection();
  });

  $(document).off("click", "#challenge-submit").on("click", "#challenge-submit", function() {
    if (typeof CTFd._internal.challenge.submitChallenge === "function") {
      CTFd._internal.challenge.submitChallenge();
    } else {
      // Trigger modal submit handler
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
        alpineData.submitChallenge();
      } else {
        CTFd._internal.challenge.submit();
      }
    }
  });

  updateQuizSelection();
  return true;
}

CTFd._internal.challenge.postRender = initQuiz;
window.addEventListener("ctfd:challenge-rendered", initQuiz);

var quizRetryCount = 0;
var quizTimer = setInterval(function() {
  quizRetryCount++;
  if (initQuiz() || quizRetryCount > 20) {
    clearInterval(quizTimer);
  }
}, 50);

CTFd._internal.challenge.submit = function(preview) {
  const $ = (window.CTFd && window.CTFd.lib && window.CTFd.lib.$) || window.$;
  const challenge_id = parseInt($("#challenge-id").val(), 10);
  const submission = $("#challenge-input").val();

  const body = {
    challenge_id: challenge_id,
    submission: submission
  };
  const params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
    if (response && response.data && response.data.status === "correct") {
      const expEl = document.getElementById("quiz-dynamic-explanation");
      if (expEl) expEl.style.display = "block";
    }
    return response;
  });
};
})();

