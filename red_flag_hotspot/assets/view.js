CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;
CTFd._internal.challenge.postRender = function() {};
CTFd._internal.challenge.submit = function() {
  return Promise.resolve();
};

CTFd.plugin.run((_CTFd) => {
  const chalIdEl = document.getElementById("challenge-id");
  if (!chalIdEl) return;
  const challengeId = chalIdEl.value;

  const configJsonEl = document.getElementById("hotspot-config-json");
  const chalInput = document.getElementById("challenge-input");
  const imgEl = document.getElementById("hotspot-target-image");
  const pinsOverlay = document.getElementById("hotspot-pins-overlay");
  const targetsOverlay = document.getElementById("hotspot-targets-overlay");
  const markersCountEl = document.getElementById("hotspot-markers-count");
  const coordsPreviewEl = document.getElementById("hotspot-coords-preview");
  const clearBtn = document.getElementById("hotspot-clear-btn");
  const submitBtn = document.getElementById("challenge-submit");

  let config = {};
  if (configJsonEl && configJsonEl.textContent) {
    try {
      config = JSON.parse(configJsonEl.textContent);
    } catch (e) {
      console.error("Failed to parse hotspot config JSON:", e);
    }
  }

  if (Object.keys(config).length === 0 && CTFd._internal.challenge.data) {
    config = CTFd._internal.challenge.data;
  }

  const maxClicks = parseInt(config.max_clicks || 5) || 5;
  const isSolved = Boolean(config.is_solved);
  const storageKey = `ctfd_hotspot_pins_${challengeId}`;

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
      pinEl.className = "position-absolute d-flex flex-column align-items-center";
      pinEl.style.left = `${pin.x}%`;
      pinEl.style.top = `${pin.y}%`;
      pinEl.style.transform = "translate(-50%, -50%)";
      pinEl.style.pointerEvents = "auto";
      pinEl.style.cursor = isSolved ? "default" : "pointer";
      pinEl.title = `Marker #${idx + 1} (${pin.x}%, ${pin.y}%). Click to remove.`;

      pinEl.innerHTML = `
        <div style="width: 24px; height: 24px; border: 2px solid #ff3b30; border-radius: 50%; background: rgba(255, 59, 48, 0.35); box-shadow: 0 0 10px #ff3b30; display: flex; align-items: center; justify-content: center; position: relative;">
          <div style="width: 6px; height: 6px; background: #ffffff; border-radius: 50%;"></div>
          <div style="position: absolute; width: 100%; height: 2px; background: rgba(255, 59, 48, 0.8);"></div>
          <div style="position: absolute; height: 100%; width: 2px; background: rgba(255, 59, 48, 0.8);"></div>
        </div>
        <span class="badge bg-danger font-monospace px-1 py-0 mt-1" style="font-size: 0.65rem;">#${idx + 1}</span>
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

    if (submitBtn) {
      submitBtn.disabled = pins.length === 0;
    }
  }

  function addPin(x, y) {
    if (isSolved) return;
    if (pins.length >= maxClicks) {
      alert(`Maximum of ${maxClicks} markers reached. Click an existing marker to remove it first.`);
      return;
    }

    pins.push({ x: Number(x.toFixed(1)), y: Number(y.toFixed(1)) });
    savePins();
    updatePins();
  }

  function removePin(index) {
    if (isSolved) return;
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
  if (imgEl) {
    imgEl.addEventListener("click", (e) => {
      const rect = imgEl.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const xPct = Math.max(0, Math.min(100, (clickX / rect.width) * 100));
      const yPct = Math.max(0, Math.min(100, (clickY / rect.height) * 100));

      addPin(xPct, yPct);
    });

    imgEl.addEventListener("mousemove", (e) => {
      if (!coordsPreviewEl) return;
      const rect = imgEl.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const xPct = Math.max(0, Math.min(100, (clickX / rect.width) * 100));
      const yPct = Math.max(0, Math.min(100, (clickY / rect.height) * 100));

      coordsPreviewEl.textContent = `X: ${xPct.toFixed(1)}% | Y: ${yPct.toFixed(1)}%`;
    });

    imgEl.addEventListener("mouseleave", () => {
      if (coordsPreviewEl) {
        coordsPreviewEl.textContent = "X: --% | Y: --%";
      }
    });
  }

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (isSolved) return;
      pins = [];
      savePins();
      updatePins();
    });
  }

  // Render revealed target zones if solved
  if (isSolved && targetsOverlay && config.hotspots_data) {
    targetsOverlay.style.display = "block";
    targetsOverlay.innerHTML = "";
    config.hotspots_data.forEach((spot, i) => {
      if (typeof spot.x === "undefined" || typeof spot.y === "undefined") return;

      const rad = parseFloat(spot.radius || config.tolerance_radius || 6.0);
      const zone = document.createElement("div");
      zone.className = "position-absolute rounded-circle border border-success border-2";
      zone.style.left = `${spot.x}%`;
      zone.style.top = `${spot.y}%`;
      zone.style.width = `${rad * 2}%`;
      zone.style.height = `${rad * 2}%`;
      zone.style.transform = "translate(-50%, -50%)";
      zone.style.background = "rgba(40, 167, 69, 0.2)";
      zone.style.boxShadow = "0 0 12px rgba(40, 167, 69, 0.6)";

      const tag = document.createElement("span");
      tag.className = "position-absolute badge bg-success font-monospace";
      tag.style.top = "-12px";
      tag.style.left = "50%";
      tag.style.transform = "translateX(-50%)";
      tag.style.fontSize = "0.65rem";
      tag.textContent = spot.label || `Target #${i + 1}`;

      zone.appendChild(tag);
      targetsOverlay.appendChild(zone);
    });
  }

  // Submit button
  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      if (chalInput) {
        chalInput.value = JSON.stringify(pins);
        chalInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const parentSubmit = document.querySelector(".submit-row button#challenge-submit");
      if (parentSubmit && parentSubmit !== submitBtn) {
        parentSubmit.click();
      } else if (window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge) {
        window.CTFd.pages.challenge.submitChallenge(challengeId, JSON.stringify(pins));
      }
    });
  }

  updatePins();
});
