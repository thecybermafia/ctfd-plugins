CTFd.plugin.run((_CTFd) => {
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return;
  const challengeId = chalIdEl.value;

  const statusAlert = document.getElementById("iu-status-alert");
  const statusIcon = document.getElementById("iu-status-icon");
  const statusTitle = document.getElementById("iu-status-title");
  const statusDesc = document.getElementById("iu-status-desc");
  const statusFeedback = document.getElementById("iu-status-feedback");
  const currentPreview = document.getElementById("iu-current-preview");
  const previewImg = document.getElementById("iu-preview-img");
  const previewLink = document.getElementById("iu-preview-link");
  const uploadFormBox = document.getElementById("iu-upload-form-box");
  const submitBtn = document.getElementById("iu-submit-btn");

  function loadStatus() {
    fetch(`/api/v1/challenges/${challengeId}/image_upload/my_status`)
      .then(r => r.json())
      .then(res => {
        if (!res.success || !res.data) return;
        const sub = res.data;
        statusAlert.classList.remove("d-none", "alert-secondary", "alert-warning", "alert-success", "alert-danger");

        if (sub.file_url) {
          currentPreview.classList.remove("d-none");
          previewImg.src = sub.file_url;
          previewLink.href = sub.file_url;
        }

        if (sub.status === "pending") {
          statusAlert.classList.add("alert-warning");
          statusIcon.className = "fas fa-clock fa-2x me-3 text-warning";
          statusTitle.textContent = "Under Administrative Review";
          statusDesc.textContent = "Your image has been submitted and is queued for judge evaluation. You may upload a new version to replace it.";
          statusFeedback.textContent = "";
        } else if (sub.status === "approved") {
          statusAlert.classList.add("alert-success");
          statusIcon.className = "fas fa-check-circle fa-2x me-3 text-success";
          statusTitle.textContent = `Approved (+${sub.points_awarded} PTS)`;
          statusDesc.textContent = "Congratulations! Your proof was verified by the judges.";
          statusFeedback.textContent = sub.feedback ? `Judge Notes: ${sub.feedback}` : "";
          if (uploadFormBox) uploadFormBox.classList.add("d-none");
          if (submitBtn) submitBtn.classList.add("d-none");
        } else if (sub.status === "rejected") {
          statusAlert.classList.add("alert-danger");
          statusIcon.className = "fas fa-times-circle fa-2x me-3 text-danger";
          statusTitle.textContent = "Submission Rejected / Revisions Needed";
          statusDesc.textContent = "The judges did not accept this submission. Please review feedback and re-upload.";
          statusFeedback.textContent = sub.feedback ? `Judge Feedback: ${sub.feedback}` : "";
        }
      })
      .catch(e => console.log("Status fetch error", e));
  }

  loadStatus();

  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      const fileInput = document.getElementById("iu-file-input");
      const notesInput = document.getElementById("iu-notes");

      if (!fileInput.files || fileInput.files.length === 0) {
        alert("Please select an image or file to upload.");
        return;
      }

      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      formData.append("notes", notesInput ? notesInput.value : "");
      formData.append("nonce", init.csrfNonce);

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Uploading...';

      fetch(`/api/v1/challenges/${challengeId}/image_upload/submit`, {
        method: "POST",
        headers: {
          "CSRF-Token": init.csrfNonce
        },
        body: formData
      })
        .then(r => r.json())
        .then(res => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i> Submit for Evaluation';

          if (res.success) {
            alert(res.message);
            fileInput.value = "";
            loadStatus();
          } else {
            alert(res.message || "Upload failed");
          }
        })
        .catch(err => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i> Submit for Evaluation';
          alert("Error submitting: " + err);
        });
    });
  }
});
