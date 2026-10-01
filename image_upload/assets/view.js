window.CTFd = window.CTFd || {};
window.CTFd._internal = window.CTFd._internal || {};
window.CTFd._internal.challenge = window.CTFd._internal.challenge || {};

window.CTFd._internal.challenge.data = undefined;
window.CTFd._internal.challenge.renderer = null;
window.CTFd._internal.challenge.preRender = function() {};
window.CTFd._internal.challenge.render = null;
window.CTFd._internal.challenge.postRender = function() {
  setTimeout(initImageUploadChallenge, 50);
};
window.CTFd._internal.challenge.submit = function() {
  return Promise.resolve();
};

function initImageUploadChallenge() {
  const container = document.getElementById("image-upload-container");
  if (!container) return false;
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return false;
  const challengeId = chalIdEl.value;

  // Ensure full width fit inside modal tab panel
  const container = document.getElementById("image-upload-container");
  if (container) {
    const col = container.closest(".col-sm-8");
    if (col) {
      col.classList.remove("col-sm-8");
      col.classList.add("col-12");
    }
    const submitRow = container.closest(".submit-row");
    if (submitRow) {
      const keySubmit = submitRow.querySelector(".key-submit");
      if (keySubmit) keySubmit.style.display = "none";
    }
  }

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

  const dropzone = document.getElementById("iu-dropzone");
  const fileInput = document.getElementById("iu-file-input");
  const dropzonePrompt = document.getElementById("iu-dropzone-prompt");
  const selectedBox = document.getElementById("iu-selected-file-box");
  const selectedName = document.getElementById("iu-selected-name");
  const selectedSize = document.getElementById("iu-selected-size");
  const selectedThumb = document.getElementById("iu-selected-thumb");
  const fileIcon = document.getElementById("iu-file-icon");
  const removeBtn = document.getElementById("iu-remove-btn");
  const changeBtn = document.getElementById("iu-change-btn");
  const fileError = document.getElementById("iu-file-error");

  let currentSelectedFile = null;

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function handleFile(file) {
    if (!file) return;

    if (fileError) {
      fileError.textContent = "";
      fileError.classList.add("d-none");
    }

    const maxSizeMb = parseFloat(fileInput.dataset.maxSize || 10);
    const maxSizeBytes = maxSizeMb * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      if (fileError) {
        fileError.textContent = `File size (${formatBytes(file.size)}) exceeds maximum allowed limit of ${maxSizeMb} MB.`;
        fileError.classList.remove("d-none");
      }
      return;
    }

    const allowedExtStr = (fileInput.dataset.allowed || "png, jpg, jpeg, webp, gif, pdf, zip").toLowerCase();
    const allowedExts = allowedExtStr.split(",").map(s => s.trim().replace(/^\./, ""));
    const fileNameParts = file.name.split(".");
    const ext = fileNameParts.length > 1 ? fileNameParts.pop().toLowerCase() : "";

    if (allowedExts.length > 0 && !allowedExts.includes(ext) && !allowedExts.includes("*")) {
      if (fileError) {
        fileError.textContent = `Extension .${ext} is not allowed. Supported formats: ${allowedExtStr.toUpperCase()}`;
        fileError.classList.remove("d-none");
      }
      return;
    }

    currentSelectedFile = file;

    // Display selected card
    if (selectedName) selectedName.textContent = file.name;
    if (selectedSize) selectedSize.textContent = formatBytes(file.size);

    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (selectedThumb) {
          selectedThumb.src = e.target.result;
          selectedThumb.classList.remove("d-none");
        }
        if (fileIcon) fileIcon.classList.add("d-none");
      };
      reader.readAsDataURL(file);
    } else {
      if (selectedThumb) {
        selectedThumb.src = "";
        selectedThumb.classList.add("d-none");
      }
      if (fileIcon) {
        fileIcon.classList.remove("d-none");
        const iconI = fileIcon.querySelector("i");
        if (iconI) {
          if (ext === "pdf") iconI.className = "fas fa-file-pdf fa-2x text-danger";
          else if (["zip", "tar", "gz"].includes(ext)) iconI.className = "fas fa-file-zipper fa-2x text-warning";
          else iconI.className = "fas fa-file-code fa-2x text-matrix-green";
        }
      }
    }

    if (dropzonePrompt) dropzonePrompt.classList.add("d-none");
    if (selectedBox) selectedBox.classList.remove("d-none");
  }

  function resetFile() {
    currentSelectedFile = null;
    if (fileInput) fileInput.value = "";
    if (selectedThumb) {
      selectedThumb.src = "";
      selectedThumb.classList.add("d-none");
    }
    if (fileIcon) fileIcon.classList.add("d-none");
    if (selectedBox) selectedBox.classList.add("d-none");
    if (dropzonePrompt) dropzonePrompt.classList.remove("d-none");
    if (fileError) {
      fileError.textContent = "";
      fileError.classList.add("d-none");
    }
  }

  // Setup Drag-and-drop & Click
  if (dropzone && !dropzone.dataset.bound) {
    dropzone.dataset.bound = "true";

    dropzone.addEventListener("click", (e) => {
      // If clicking remove or change, let those handlers deal with it
      if (e.target.closest("#iu-remove-btn") || e.target.closest("#iu-change-btn")) return;
      if (!currentSelectedFile && fileInput) {
        fileInput.click();
      }
    });

    ["dragenter", "dragover"].forEach(evt => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("iu-dragover");
      });
    });

    ["dragleave", "dragend"].forEach(evt => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("iu-dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("iu-dragover");

      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        handleFile(file);
      }
    });
  }

  if (fileInput && !fileInput.dataset.bound) {
    fileInput.dataset.bound = "true";
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFile(fileInput.files[0]);
      }
    });
  }

  if (removeBtn && !removeBtn.dataset.bound) {
    removeBtn.dataset.bound = "true";
    removeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      resetFile();
    });
  }

  if (changeBtn && !changeBtn.dataset.bound) {
    changeBtn.dataset.bound = "true";
    changeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (fileInput) fileInput.click();
    });
  }

  function loadStatus() {
    fetch(`/api/v1/challenges/${challengeId}/image_upload/my_status`)
      .then(r => r.json())
      .then(res => {
        if (!res.success || !res.data) return;
        const sub = res.data;
        if (!statusAlert) return;

        statusAlert.classList.remove("d-none", "alert-secondary", "alert-warning", "alert-success", "alert-danger");

        if (sub.file_url) {
          if (currentPreview) currentPreview.classList.remove("d-none");
          if (previewImg) previewImg.src = sub.file_url;
          if (previewLink) previewLink.href = sub.file_url;
        }

        if (sub.status === "pending") {
          statusAlert.classList.add("alert-warning");
          if (statusIcon) statusIcon.className = "fas fa-clock-rotate-left fa-2x me-3 text-warning";
          if (statusTitle) statusTitle.textContent = "TRANSMISSION UNDER ADMINISTRATIVE EVALUATION";
          if (statusDesc) statusDesc.textContent = "Your telemetry proof is queued for judge evaluation. You may submit a revised proof if needed.";
          if (statusFeedback) statusFeedback.textContent = "";
        } else if (sub.status === "approved") {
          statusAlert.classList.add("alert-success");
          if (statusIcon) statusIcon.className = "fas fa-shield-check fa-2x me-3 text-success";
          if (statusTitle) statusTitle.textContent = `MISSION VERIFIED & APPROVED (+${sub.points_awarded} PTS)`;
          if (statusDesc) statusDesc.textContent = "Target verification confirmed by evaluators.";
          if (statusFeedback) statusFeedback.textContent = sub.feedback ? `Evaluator Notes: ${sub.feedback}` : "";
          if (uploadFormBox) uploadFormBox.classList.add("d-none");
          if (submitBtn) submitBtn.classList.add("d-none");
        } else if (sub.status === "rejected") {
          statusAlert.classList.add("alert-danger");
          if (statusIcon) statusIcon.className = "fas fa-circle-exclamation fa-2x me-3 text-danger";
          if (statusTitle) statusTitle.textContent = "PROOF REJECTED / REVISION REQUIRED";
          if (statusDesc) statusDesc.textContent = "The submitted evidence did not satisfy mission requirements. Review notes below and re-transmit.";
          if (statusFeedback) statusFeedback.textContent = sub.feedback ? `Evaluator Feedback: ${sub.feedback}` : "";
        }
      })
      .catch(e => {
        // Silent catch for network drops
      });
  }

  loadStatus();

  if (submitBtn && !submitBtn.dataset.bound) {
    submitBtn.dataset.bound = "true";
    submitBtn.addEventListener("click", () => {
      const file = currentSelectedFile || (fileInput.files && fileInput.files[0]);
      const notesInput = document.getElementById("iu-notes");

      if (!file) {
        alert("Please drop or select an evidence screenshot before submitting.");
        return;
      }

      const csrfToken = (window.init && window.init.csrfNonce) || (window.CTFd && window.CTFd.config && window.CTFd.config.csrfNonce) || "";
      const formData = new FormData();
      formData.append("file", file);
      formData.append("notes", notesInput ? notesInput.value : "");
      formData.append("nonce", csrfToken);

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i> Transmitting Proof...';

      fetch(`/api/v1/challenges/${challengeId}/image_upload/submit`, {
        method: "POST",
        headers: {
          "CSRF-Token": csrfToken
        },
        body: formData
      })
        .then(r => r.json())
        .then(res => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-satellite-dish me-2"></i> Transmit Proof for Mission Review';

          if (res.success) {
            alert(res.message);
            resetFile();
            loadStatus();
          } else {
            alert(res.message || "Upload failed");
          }
        })
        .catch(err => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-satellite-dish me-2"></i> Transmit Proof for Mission Review';
          alert("Error submitting: " + err);
        });
    });
  }
  return true;
}

CTFd._internal.challenge.postRender = initImageUploadChallenge;
window.addEventListener("ctfd:challenge-rendered", initImageUploadChallenge);

let iuRetryCount = 0;
const iuTimer = setInterval(function() {
  iuRetryCount++;
  if (initImageUploadChallenge() || iuRetryCount > 20) {
    clearInterval(iuTimer);
  }
}, 50);

document.addEventListener("shown.bs.modal", () => {
  setTimeout(initImageUploadChallenge, 50);
});

if (window.CTFd && window.CTFd.plugin && window.CTFd.plugin.run) {
  window.CTFd.plugin.run(() => {
    setTimeout(initImageUploadChallenge, 100);
  });
}
