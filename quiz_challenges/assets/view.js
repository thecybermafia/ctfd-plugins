CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function() {
  const $ = (window.CTFd && window.CTFd.lib && window.CTFd.lib.$) || window.$;
  if (!$) return;

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
          "border-color": "var(--cyber-cyan, #0dcaf0)",
          "background": "rgba(13, 202, 240, 0.12)"
        });
      } else {
        $(this).css({
          "border-color": "rgba(255, 255, 255, 0.15)",
          "background": "rgba(15, 23, 42, 0.7)"
        });
      }
    });

    if (selected.length > 0) {
      $("#challenge-input").val(selected.join(","));
      $("#challenge-submit").prop("disabled", false);
    } else {
      $("#challenge-input").val("");
      $("#challenge-submit").prop("disabled", true);
    }
  }

  $(document).off("change", ".quiz-option-input").on("change", ".quiz-option-input", function() {
    updateQuizSelection();
  });

  updateQuizSelection();
};

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
    if (response.status === 429) {
      return response;
    }
    if (response.status === 403) {
      return response;
    }
    return response;
  });
};
