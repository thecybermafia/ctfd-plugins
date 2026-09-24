CTFd.plugin.run((_CTFd) => {
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return;
  const challengeId = chalIdEl.value;

  const statusAlert = document.getElementById("ta-status-alert");
  const statusIcon = document.getElementById("ta-status-icon");
  const statusTitle = document.getElementById("ta-status-title");
  const statusDesc = document.getElementById("ta-status-desc");
  const statusFeedback = document.getElementById("ta-status-feedback");
  const contentInput = document.getElementById("ta-content-input");
  const charCounter = document.getElementById("ta-char-counter");
  const submitBtn = document.getElementById("ta-submit-btn");
  const formBox = document.getElementById("ta-form-box");

  function updateCharCount() {
    if (!contentInput || !charCounter) return;
    const len = contentInput.value.length;
    const max = contentInput.getAttribute("maxlength") || "5000";
    charCounter.textContent = `${len} / ${max} chars`;
  }

  if (contentInput) {
    contentInput.addEventListener("input", updateCharCount);
  }

  function loadStatus() {
    fetch(`/api/v1/challenges/${challengeId}/textarea/my_status`)
      .then(r => r.json())
      .then(res => {
        if (!res.success || !res.data) return;
        const sub = res.data;
        statusAlert.classList.remove("d-none", "alert-secondary", "alert-warning", "alert-success", "alert-danger");

        if (contentInput && sub.content && !contentInput.value) {
          contentInput.value = sub.content;
          updateCharCount();
        }

        if (sub.status === "pending") {
          statusAlert.classList.add("alert-warning");
          statusIcon.className = "fas fa-clock fa-2x me-3 text-warning";
          statusTitle.textContent = "Under Administrative Review";
          statusDesc.textContent = "Your writeup has been submitted and is queued for judge evaluation. You may update your text to resubmit.";
          statusFeedback.textContent = "";
        } else if (sub.status === "approved") {
          statusAlert.classList.add("alert-success");
          statusIcon.className = "fas fa-check-circle fa-2x me-3 text-success";
          statusTitle.textContent = `Approved (+${sub.points_awarded} PTS)`;
          statusDesc.textContent = "Congratulations! Your writeup was verified and points have been credited.";
          statusFeedback.textContent = sub.feedback ? `Judge Feedback: ${sub.feedback}` : "";
          if (contentInput) contentInput.disabled = true;
          if (submitBtn) submitBtn.classList.add("d-none");
        } else if (sub.status === "rejected") {
          statusAlert.classList.add("alert-danger");
          statusIcon.className = "fas fa-times-circle fa-2x me-3 text-danger";
          statusTitle.textContent = "Submission Rejected / Revision Needed";
          statusDesc.textContent = "The judges requested revisions for this submission. Please review the feedback below and update your response.";
          statusFeedback.textContent = sub.feedback ? `Judge Feedback: ${sub.feedback}` : "";
        }
      })
      .catch(err => {
        console.error("Failed to load textarea submission status:", err);
      });
  }

  loadStatus();

  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      const text = contentInput ? contentInput.value.trim() : "";
      if (!text) {
        alert("Please enter your writeup or solution text before submitting.");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Submitting...';

      fetch(`/api/v1/challenges/${challengeId}/textarea/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "CSRF-Token": init.csrfNonce
        },
        body: JSON.stringify({
          content: text,
          nonce: init.csrfNonce
        })
      })
        .then(r => r.json())
        .then(res => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i> Submit for Evaluation';

          if (res.success) {
            alert(res.message);
            loadStatus();
          } else {
            alert(res.message || "Submission failed");
          }
        })
        .catch(err => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i> Submit for Evaluation';
          alert("Network communication error. Please try again.");
          console.error("Submission error:", err);
        });
    });
  }
});
