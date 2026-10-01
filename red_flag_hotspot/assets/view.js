(function() {
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

function initRedFlagHotspot() {
  const container = document.querySelector(".red-flag-hotspot-container");
  if (!container) return false;

  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return false;
  const challengeId = chalIdEl.value;

  const configJsonEl = document.getElementById("hotspot-config-json");
  const chalInput = document.getElementById("challenge-input");
  const imgEl = document.getElementById("hotspot-target-image");
  const pinsOverlay = document.getElementById("hotspot-pins-overlay");
  const targetsOverlay = document.getElementById("hotspot-targets-overlay");
  const markersCountEl = document.getElementById("hotspot-markers-count");
  const clearBtn = document.getElementById("hotspot-clear-btn");
  const submitBtn = document.getElementById("rfh-submit-btn");
  const zoomBtn = document.getElementById("hotspot-zoom-btn");
  const feedbackAlert = document.getElementById("rfh-feedback-alert");

  let config = {};
  if (configJsonEl && configJsonEl.textContent) {
    try {
      config = JSON.parse(configJsonEl.textContent);
    } catch (e) {
      console.error("Failed to parse hotspot config JSON:", e);
    }
  }

  const maxClicks = parseInt(config.max_clicks || 5) || 5;
  const minRequired = parseInt(config.min_hits_required || 3) || 3;
  const isSolved = Boolean(config.is_solved);
  const storageKey = `ctfd_hotspot_pins_${challengeId}`;

  // Ensure full width in modal submit row
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

  // Standalone Lightbox controls
  const lightboxModal = document.getElementById("rfh-lightbox-modal");
  const lightboxImg = document.getElementById("rfh-lightbox-image");
  const closeBtn = document.getElementById("rfh-lightbox-close-btn");
  const zoomInBtn = document.getElementById("rfh-zoom-in-btn");
  const zoomOutBtn = document.getElementById("rfh-zoom-out-btn");
  const zoomResetBtn = document.getElementById("rfh-zoom-reset-btn");
  let currentZoom = 1.0;

  function updateZoom(factor) {
    currentZoom = Math.min(3.0, Math.max(0.5, factor));
    if (lightboxImg) {
      lightboxImg.style.transform = `scale(${currentZoom})`;
      lightboxImg.style.cursor = currentZoom > 1.0 ? "zoom-out" : "zoom-in";
    }
    if (zoomResetBtn) {
      zoomResetBtn.textContent = `${Math.round(currentZoom * 100)}%`;
    }
  }

  function openLightbox() {
    if (!lightboxModal) return;
    if (lightboxModal.parentElement !== document.body) {
      document.body.appendChild(lightboxModal);
    }
    currentZoom = 1.0;
    updateZoom(1.0);
    lightboxModal.classList.remove("d-none");
    document.addEventListener("keydown", handleLightboxKey);
  }

  function closeLightbox() {
    if (!lightboxModal) return;
    lightboxModal.classList.add("d-none");
    document.removeEventListener("keydown", handleLightboxKey);
  }

  function handleLightboxKey(e) {
    if (e.key === "Escape") {
      closeLightbox();
    }
  }

  if (zoomBtn && !zoomBtn.dataset.bound) {
    zoomBtn.dataset.bound = "true";
    zoomBtn.addEventListener("click", openLightbox);
  }

  if (closeBtn && !closeBtn.dataset.bound) {
    closeBtn.dataset.bound = "true";
    closeBtn.addEventListener("click", closeLightbox);
  }

  const backdrop = lightboxModal ? lightboxModal.querySelector(".rfh-lightbox-backdrop") : null;
  if (backdrop && !backdrop.dataset.bound) {
    backdrop.dataset.bound = "true";
    backdrop.addEventListener("click", closeLightbox);
  }

  if (zoomInBtn && !zoomInBtn.dataset.bound) {
    zoomInBtn.dataset.bound = "true";
    zoomInBtn.addEventListener("click", () => updateZoom(currentZoom + 0.25));
  }
  if (zoomOutBtn && !zoomOutBtn.dataset.bound) {
    zoomOutBtn.dataset.bound = "true";
    zoomOutBtn.addEventListener("click", () => updateZoom(currentZoom - 0.25));
  }
  if (zoomResetBtn && !zoomResetBtn.dataset.bound) {
    zoomResetBtn.dataset.bound = "true";
    zoomResetBtn.addEventListener("click", () => updateZoom(1.0));
  }
  if (lightboxImg && !lightboxImg.dataset.bound) {
    lightboxImg.dataset.bound = "true";
    lightboxImg.addEventListener("click", () => {
      if (currentZoom === 1.0) updateZoom(1.75);
      else updateZoom(1.0);
    });
  }

  let pins = [];
  try {
    pins = JSON.parse(localStorage.getItem(storageKey) || "[]");
  } catch (e) {
    pins = [];
  }

  function updatePins() {
    if (!pinsOverlay) return;
    pinsOverlay.innerHTML = "";

    pins.forEach((pin, idx) => {
      const pinEl = document.createElement("div");
      pinEl.className = "position-absolute d-flex flex-column align-items-center rfh-pin";
      pinEl.style.left = `${pin.x}%`;
      pinEl.style.top = `${pin.y}%`;
      pinEl.style.transform = "translate(-50%, -50%)";
      pinEl.style.pointerEvents = "auto";
      pinEl.style.cursor = isSolved ? "default" : "pointer";
      pinEl.title = `Pin #${idx + 1}. Click to remove.`;

      pinEl.innerHTML = `
        <div class="rfh-pin-reticle">
          <div class="rfh-pin-center"></div>
          <div class="rfh-pin-h-line"></div>
          <div class="rfh-pin-v-line"></div>
        </div>
        <span class="badge bg-danger font-monospace px-1 py-0 mt-1 rfh-pin-badge">#${idx + 1}</span>
      `;

      if (!isSolved) {
        pinEl.addEventListener("click", (e) => {
          e.stopPropagation();
          removePin(idx);
        });
      }

      pinsOverlay.appendChild(pinEl);
    });

    if (markersCountEl) {
      markersCountEl.textContent = pins.length;
    }

    if (chalInput) {
      chalInput.value = JSON.stringify(pins);
      chalInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (submitBtn && !isSolved) {
      if (pins.length >= minRequired) {
        submitBtn.disabled = false;
        submitBtn.className = "challenge-submit btn btn-success w-100 py-2 fw-bold font-monospace text-uppercase rfh-submit-btn";
        submitBtn.innerHTML = `<i class="fas fa-check me-2"></i> Submit (${pins.length} pin${pins.length > 1 ? 's' : ''} placed)`;
      } else {
        submitBtn.disabled = true;
        submitBtn.className = "challenge-submit btn btn-outline-secondary w-100 py-2 fw-bold font-monospace text-uppercase rfh-submit-btn";
        const needed = minRequired - pins.length;
        if (pins.length === 0) {
          submitBtn.innerHTML = `Click suspicious areas to place pins (need at least ${minRequired})`;
        } else {
          submitBtn.innerHTML = `Place ${needed} more pin${needed > 1 ? 's' : ''} (${pins.length}/${minRequired})`;
        }
      }
    }
  }

  function addPin(x, y) {
    if (isSolved) return;
    if (feedbackAlert) feedbackAlert.classList.add("d-none");
    if (pins.length >= maxClicks) {
      if (feedbackAlert) {
        feedbackAlert.className = "alert alert-warning my-2 text-center font-monospace border border-warning";
        feedbackAlert.innerHTML = `<i class="fas fa-info-circle me-2"></i> Maximum of ${maxClicks} pins reached. Click an existing pin to remove it before adding another.`;
        feedbackAlert.classList.remove("d-none");
      }
      return;
    }

    pins.push({ x: Number(x.toFixed(1)), y: Number(y.toFixed(1)) });
    savePins();
    updatePins();
  }

  function removePin(index) {
    if (isSolved) return;
    if (feedbackAlert) feedbackAlert.classList.add("d-none");
    pins.splice(index, 1);
    savePins();
    updatePins();
  }

  function savePins() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(pins));
    } catch (e) {}
  }

  // Bind image click listener
  if (imgEl && !imgEl.dataset.bound) {
    imgEl.dataset.bound = "true";
    imgEl.addEventListener("click", (e) => {
      if (isSolved) return;
      const rect = imgEl.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const xPct = Math.max(0, Math.min(100, (clickX / rect.width) * 100));
      const yPct = Math.max(0, Math.min(100, (clickY / rect.height) * 100));

      addPin(xPct, yPct);
    });
  }

  // Clear button
  if (clearBtn && !clearBtn.dataset.bound) {
    clearBtn.dataset.bound = "true";
    clearBtn.addEventListener("click", () => {
      if (isSolved) return;
      if (feedbackAlert) feedbackAlert.classList.add("d-none");
      pins = [];
      savePins();
      updatePins();
    });
  }

  // Render revealed target zones if solved
  if (isSolved && targetsOverlay && config.hotspots_data && config.hotspots_data.length > 0) {
    targetsOverlay.style.display = "block";
    targetsOverlay.innerHTML = "";
    config.hotspots_data.forEach((spot, i) => {
      if (typeof spot.x === "undefined" || typeof spot.y === "undefined") return;

      const rad = parseFloat(spot.radius || config.tolerance_radius || 8.0);
      const zone = document.createElement("div");
      zone.className = "position-absolute rounded-circle border border-success border-2";
      zone.style.left = `${spot.x}%`;
      zone.style.top = `${spot.y}%`;
      zone.style.width = `${rad * 2}%`;
      zone.style.height = `${rad * 2}%`;
      zone.style.transform = "translate(-50%, -50%)";
      zone.style.background = "rgba(0, 230, 118, 0.22)";
      zone.style.boxShadow = "0 0 16px rgba(0, 230, 118, 0.65)";

      const tag = document.createElement("span");
      tag.className = "position-absolute badge bg-success text-dark font-monospace fw-bold";
      tag.style.top = "-14px";
      tag.style.left = "50%";
      tag.style.transform = "translateX(-50%)";
      tag.style.fontSize = "0.7rem";
      tag.style.whiteSpace = "nowrap";
      tag.textContent = spot.label || `Red Flag #${i + 1}`;

      zone.appendChild(tag);
      targetsOverlay.appendChild(zone);
    });
  }

  // Submit button
  if (submitBtn && !submitBtn.dataset.bound) {
    submitBtn.dataset.bound = "true";
    submitBtn.addEventListener("click", async () => {
      if (pins.length < minRequired) {
        if (feedbackAlert) {
          feedbackAlert.className = "alert alert-warning my-2 text-center font-monospace border border-warning";
          feedbackAlert.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i> Please mark at least ${minRequired} suspicious areas before submitting.`;
          feedbackAlert.classList.remove("d-none");
        }
        return;
      }

      if (feedbackAlert) {
        feedbackAlert.classList.add("d-none");
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i> Verifying Red Flags...';

      const payload = JSON.stringify(pins);
      if (chalInput) {
        chalInput.value = payload;
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }

      try {
        let res = null;
        if (window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge) {
          res = await window.CTFd.pages.challenge.submitChallenge(challengeId, payload);
        } else {
          const csrf = (window.init && window.init.csrfNonce) || (window.CTFd && window.CTFd.config && window.CTFd.config.csrfNonce) || "";
          const fetchRes = await fetch("/api/v1/challenges/attempt", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "CSRF-Token": csrf
            },
            body: JSON.stringify({
              challenge_id: challengeId,
              submission: payload
            })
          });
          res = await fetchRes.json();
        }

        const status = res && res.data ? res.data.status : (res && res.status ? res.status : null);
        const message = res && res.data && res.data.message ? res.data.message : (res && res.message ? res.message : "");

        if (status === "correct") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-success my-2 text-center font-monospace border border-success";
            feedbackAlert.innerHTML = `<i class="fas fa-check-circle me-2"></i> <strong>${message || "Spot-the-Red-Flag Success!"}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          submitBtn.className = "challenge-submit btn btn-success w-100 py-2 fw-bold font-monospace text-uppercase rfh-submit-btn";
          submitBtn.innerHTML = '<i class="fas fa-check-double me-2"></i> Challenge Solved!';
          submitBtn.disabled = true;

          if (window.WorldAudio && typeof window.WorldAudio.playSolve === "function") {
            window.WorldAudio.playSolve();
          }
          if (typeof window.confetti === "function") {
            window.confetti();
          }

          try { localStorage.removeItem(storageKey); } catch(e){}

          // Sync with Alpine Challenge modal
          const chalModal = container ? container.closest('[x-data]') : document.querySelector('[x-data="Challenge"]');
          if (chalModal && window.Alpine && window.Alpine.$data) {
            try {
              const alpineData = window.Alpine.$data(chalModal);
              if (alpineData) {
                alpineData.response = res;
                alpineData.submission = "";
                if (typeof alpineData.renderSubmissionResponse === "function") {
                  alpineData.renderSubmissionResponse();
                }
              }
            } catch (e) {}
          }

          setTimeout(() => {
            window.location.reload();
          }, 1200);

        } else if (status === "already_solved") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-info my-2 text-center font-monospace border border-info";
            feedbackAlert.innerHTML = `<i class="fas fa-info-circle me-2"></i> <strong>${message || "You have already solved this challenge."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          submitBtn.disabled = true;
          setTimeout(() => { window.location.reload(); }, 1200);

        } else if (status === "incorrect") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-danger my-2 text-center font-monospace border border-danger";
            feedbackAlert.innerHTML = `<i class="fas fa-circle-xmark me-2"></i> <strong>${message || "Incorrect red flags identified. Review the evidence carefully."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          if (window.WorldAudio && typeof window.WorldAudio.playError === "function") {
            window.WorldAudio.playError();
          }

          // Sync with Alpine so attempts counter increments
          const chalModal = container ? container.closest('[x-data]') : document.querySelector('[x-data="Challenge"]');
          if (chalModal && window.Alpine && window.Alpine.$data) {
            try {
              const alpineData = window.Alpine.$data(chalModal);
              if (alpineData) {
                alpineData.response = res;
                if (typeof alpineData.renderSubmissionResponse === "function") {
                  alpineData.renderSubmissionResponse();
                }
              }
            } catch (e) {}
          }

          submitBtn.disabled = false;
          updatePins();

        } else if (status === "ratelimited") {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-warning my-2 text-center font-monospace border border-warning";
            feedbackAlert.innerHTML = `<i class="fas fa-stopwatch me-2"></i> <strong>${message || "You are submitting too fast. Please wait a few seconds and try again."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          let countdown = 3;
          submitBtn.disabled = true;
          submitBtn.innerHTML = `<i class="fas fa-stopwatch me-2"></i> Wait ${countdown}s...`;
          const timer = setInterval(() => {
            countdown--;
            if (countdown > 0) {
              submitBtn.innerHTML = `<i class="fas fa-stopwatch me-2"></i> Wait ${countdown}s...`;
            } else {
              clearInterval(timer);
              submitBtn.disabled = false;
              updatePins();
            }
          }, 1000);

        } else {
          if (feedbackAlert) {
            feedbackAlert.className = "alert alert-warning my-2 text-center font-monospace border border-warning";
            feedbackAlert.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i> <strong>${message || "Unexpected response. Please try again."}</strong>`;
            feedbackAlert.classList.remove("d-none");
          }
          submitBtn.disabled = false;
          updatePins();
        }

      } catch (err) {
        console.error("RedFlagHotspot submission failed:", err);
        if (feedbackAlert) {
          feedbackAlert.className = "alert alert-danger my-2 text-center font-monospace border border-danger";
          feedbackAlert.innerHTML = `<i class="fas fa-circle-exclamation me-2"></i> <strong>Submission failed. Please check your connection and try again.</strong>`;
          feedbackAlert.classList.remove("d-none");
        }
        submitBtn.disabled = false;
        updatePins();
      }
    });
  }

  updatePins();
  return true;
}

CTFd._internal.challenge.postRender = initRedFlagHotspot;
window.addEventListener("ctfd:challenge-rendered", initRedFlagHotspot);

var rfhRetryCount = 0;
var rfhTimer = setInterval(function() {
  rfhRetryCount++;
  if (initRedFlagHotspot() || rfhRetryCount > 20) {
    clearInterval(rfhTimer);
  }
}, 50);

document.addEventListener("shown.bs.modal", () => {
  setTimeout(initRedFlagHotspot, 50);
});

if (window.CTFd && window.CTFd.plugin && window.CTFd.plugin.run) {
  window.CTFd.plugin.run(() => {
    setTimeout(initRedFlagHotspot, 100);
  });
}

CTFd._internal.challenge.submit = function(preview) {
  const chalIdEl = document.getElementById("challenge-id");
  const chalInput = document.getElementById("challenge-input");
  if (!chalIdEl || !chalInput) return Promise.resolve();

  const challenge_id = parseInt(chalIdEl.value, 10);
  const submission = chalInput.value;

  const body = {
    challenge_id: challenge_id,
    submission: submission
  };
  const params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body);
};
})();
