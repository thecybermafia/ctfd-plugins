/**
 * Red Flag Hotspot - Visual Admin Editor
 * Provides drag-and-drop file upload for SVG/PNG/JPG evidence images
 * and an interactive visual canvas for defining red flag bounding boxes and circle targets.
 */
(function() {
  function initRedFlagHotspotAdmin() {
    const container = document.getElementById("rfh-admin-editor-root");
    if (!container || container.dataset.initialized === "true") return;
    container.dataset.initialized = "true";

    const fileInput = document.getElementById("rfh-admin-file-input");
    const dropzone = document.getElementById("rfh-admin-dropzone");
    const browseBtn = document.getElementById("rfh-admin-browse-btn");
    const uploadStatus = document.getElementById("rfh-admin-upload-status");
    const imageUrlInput = document.getElementById("rfh-admin-image-url");
    const loadUrlBtn = document.getElementById("rfh-admin-load-url-btn");
    const mediaBar = document.getElementById("rfh-admin-media-bar");
    const mediaThumb = document.getElementById("rfh-admin-media-thumb");
    const mediaName = document.getElementById("rfh-admin-media-name");
    const replaceImageBtn = document.getElementById("rfh-admin-replace-btn");
    const toggleUrlBtn = document.getElementById("rfh-admin-toggle-url-btn");
    const urlContainer = document.getElementById("rfh-admin-url-container");

    const canvasWrapper = document.getElementById("rfh-admin-canvas-wrapper");
    const canvasEmpty = document.getElementById("rfh-admin-canvas-empty");
    const canvasInner = document.getElementById("rfh-admin-canvas-inner");
    const previewImg = document.getElementById("rfh-admin-preview-img");
    const overlay = document.getElementById("rfh-admin-overlay");
    const dragBox = document.getElementById("rfh-admin-drag-box");

    const modeBoxBtn = document.getElementById("rfh-mode-box-btn");
    const modePointBtn = document.getElementById("rfh-mode-point-btn");
    const helpText = document.getElementById("rfh-canvas-help-text");
    const clearAllBtn = document.getElementById("rfh-admin-clear-all-btn");
    const expandBtn = document.getElementById("rfh-admin-expand-btn");

    const zoomInBtn = document.getElementById("rfh-canvas-zoom-in");
    const zoomOutBtn = document.getElementById("rfh-canvas-zoom-out");
    const zoomResetBtn = document.getElementById("rfh-canvas-zoom-reset");

    const hotspotsList = document.getElementById("rfh-hotspots-list");
    const hotspotsJsonArea = document.getElementById("rfh-hotspots-json-textarea");
    const counterBadge = document.getElementById("rfh-hotspot-counter");
    const listCount = document.getElementById("rfh-list-count");

    let hotspots = [];
    let currentMode = "box"; // "box" or "point"
    let isDragging = false;
    let startX = 0, startY = 0;
    let canvasZoom = 1.0;

    // Load initial hotspots from textarea if available
    if (hotspotsJsonArea && hotspotsJsonArea.value.trim()) {
      try {
        const parsed = JSON.parse(hotspotsJsonArea.value.trim());
        if (Array.isArray(parsed)) {
          hotspots = parsed;
        }
      } catch (e) {
        console.warn("Could not parse existing hotspots_json:", e);
      }
    }

    // Full width layout toggle
    if (expandBtn) {
      expandBtn.addEventListener("click", () => {
        const updateCol = document.getElementById("challenge-update-container");
        if (!updateCol) return;
        const leftCol = updateCol.previousElementSibling;
        const isExpanded = updateCol.classList.contains("col-md-12");

        if (isExpanded) {
          updateCol.classList.remove("col-md-12");
          updateCol.classList.add("col-md-6");
          if (leftCol) leftCol.style.display = "";
          expandBtn.innerHTML = '<i class="fas fa-expand-alt me-1"></i> Widescreen';
          expandBtn.classList.remove("btn-primary");
          expandBtn.classList.add("btn-outline-secondary");
        } else {
          updateCol.classList.remove("col-md-6");
          updateCol.classList.add("col-md-12");
          if (leftCol) leftCol.style.display = "none";
          expandBtn.innerHTML = '<i class="fas fa-compress-alt me-1"></i> Compact View';
          expandBtn.classList.remove("btn-outline-secondary");
          expandBtn.classList.add("btn-primary");
        }
      });
    }

    // Canvas zoom controls
    function setCanvasZoom(val) {
      canvasZoom = Math.min(2.5, Math.max(0.5, val));
      if (canvasInner) {
        canvasInner.style.transform = `scale(${canvasZoom})`;
        canvasInner.style.transformOrigin = "top center";
      }
      if (zoomResetBtn) {
        zoomResetBtn.textContent = `${Math.round(canvasZoom * 100)}%`;
      }
    }

    if (zoomInBtn) zoomInBtn.addEventListener("click", () => setCanvasZoom(canvasZoom + 0.15));
    if (zoomOutBtn) zoomOutBtn.addEventListener("click", () => setCanvasZoom(canvasZoom - 0.15));
    if (zoomResetBtn) zoomResetBtn.addEventListener("click", () => setCanvasZoom(1.0));

    // Mode toggling
    function setMode(mode) {
      currentMode = mode;
      if (mode === "box") {
        if (modeBoxBtn) {
          modeBoxBtn.classList.add("active", "btn-primary");
          modeBoxBtn.classList.remove("btn-outline-primary");
        }
        if (modePointBtn) {
          modePointBtn.classList.remove("active", "btn-primary");
          modePointBtn.classList.add("btn-outline-primary");
        }
        if (helpText) {
          helpText.innerHTML = '<i class="fas fa-vector-square text-primary me-1"></i> Click and drag on image to draw a <strong>bounding box</strong>.';
        }
      } else {
        if (modePointBtn) {
          modePointBtn.classList.add("active", "btn-primary");
          modePointBtn.classList.remove("btn-outline-primary");
        }
        if (modeBoxBtn) {
          modeBoxBtn.classList.remove("active", "btn-primary");
          modeBoxBtn.classList.add("btn-outline-primary");
        }
        if (helpText) {
          helpText.innerHTML = '<i class="fas fa-map-pin text-danger me-1"></i> Click anywhere on image to place a <strong>circular target pin</strong>.';
        }
      }
    }

    if (modeBoxBtn) modeBoxBtn.addEventListener("click", () => setMode("box"));
    if (modePointBtn) modePointBtn.addEventListener("click", () => setMode("point"));

    // Sync state: updates textarea, counter, list, and canvas overlays
    function syncState() {
      if (hotspotsJsonArea) {
        hotspotsJsonArea.value = JSON.stringify(hotspots, null, 2);
        hotspotsJsonArea.dispatchEvent(new Event("change", { bubbles: true }));
      }
      const count = hotspots.length;
      if (counterBadge) counterBadge.textContent = `${count} Target${count === 1 ? '' : 's'}`;
      if (listCount) listCount.textContent = count;

      renderHotspotsOnCanvas();
      renderHotspotsList();
    }

    // Render visual targets on canvas
    function renderHotspotsOnCanvas() {
      if (!overlay) return;
      overlay.innerHTML = "";

      hotspots.forEach((spot, idx) => {
        const itemEl = document.createElement("div");
        itemEl.className = "position-absolute rfh-canvas-target";
        itemEl.setAttribute("data-spot-idx", idx);
        itemEl.style.pointerEvents = "auto";

        const labelText = spot.label || `Target #${idx + 1}`;
        const isBox = spot.x_min !== undefined && spot.x_max !== undefined;

        if (isBox) {
          const left = Math.min(spot.x_min, spot.x_max);
          const top = Math.min(spot.y_min, spot.y_max);
          const width = Math.max(1, Math.abs(spot.x_max - spot.x_min));
          const height = Math.max(1, Math.abs(spot.y_max - spot.y_min));

          itemEl.style.left = `${left}%`;
          itemEl.style.top = `${top}%`;
          itemEl.style.width = `${width}%`;
          itemEl.style.height = `${height}%`;
          itemEl.style.border = "2px dashed #00e676";
          itemEl.style.background = "rgba(0, 230, 118, 0.18)";
          itemEl.style.boxShadow = "0 0 10px rgba(0, 230, 118, 0.45)";
          itemEl.style.borderRadius = "3px";

          // If top < 8%, position badge INSIDE the box so it never gets clipped!
          const badgeStyle = top < 8
            ? "top: 2px; left: 2px;"
            : "top: -16px; left: 0;";

          itemEl.innerHTML = `
            <div class="position-absolute d-flex align-items-center gap-1 bg-dark text-white px-1 font-monospace rounded shadow-sm border border-success" style="${badgeStyle} font-size: 0.68rem; white-space: nowrap; z-index: 10;">
              <span class="badge bg-success p-0 px-1">#${idx + 1}</span>
              <span class="rfh-target-label-text">${escapeHtml(labelText)}</span>
              <button type="button" class="btn btn-link text-danger p-0 ms-1 rfh-del-btn" style="line-height: 1; font-size: 0.85rem;" title="Delete this target">&times;</button>
            </div>
          `;
        } else {
          // Circular target
          const cx = spot.x !== undefined ? spot.x : 50;
          const cy = spot.y !== undefined ? spot.y : 50;
          const r = parseFloat(spot.radius || 8.0);

          itemEl.style.left = `${cx}%`;
          itemEl.style.top = `${cy}%`;
          itemEl.style.width = `${r * 2}%`;
          itemEl.style.height = `${r * 2}%`;
          itemEl.style.transform = "translate(-50%, -50%)";
          itemEl.style.borderRadius = "50%";
          itemEl.style.border = "2px solid #ff2d55";
          itemEl.style.background = "rgba(255, 45, 85, 0.25)";
          itemEl.style.boxShadow = "0 0 12px rgba(255, 45, 85, 0.6)";

          // If cy < 10%, position badge BELOW the circle so it never gets clipped!
          const badgeStyle = cy < 10
            ? "top: 100%; left: 50%; transform: translateX(-50%); margin-top: 2px;"
            : "top: -18px; left: 50%; transform: translateX(-50%);";

          itemEl.innerHTML = `
            <div class="position-absolute top-50 start-50 translate-middle rounded-circle bg-white" style="width: 6px; height: 6px;"></div>
            <div class="position-absolute d-flex align-items-center gap-1 bg-dark text-white px-1 font-monospace rounded shadow-sm border border-danger" style="${badgeStyle} font-size: 0.68rem; white-space: nowrap; z-index: 10;">
              <span class="badge bg-danger p-0 px-1">#${idx + 1}</span>
              <span class="rfh-target-label-text">${escapeHtml(labelText)}</span>
              <button type="button" class="btn btn-link text-danger p-0 ms-1 rfh-del-btn" style="line-height: 1; font-size: 0.85rem;" title="Delete this target">&times;</button>
            </div>
          `;
        }

        // Delete button click on overlay
        const delBtn = itemEl.querySelector(".rfh-del-btn");
        if (delBtn) {
          delBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            deleteHotspot(idx);
          });
        }

        // Highlight matching list card on hover
        itemEl.addEventListener("mouseenter", () => highlightHotspot(idx, true));
        itemEl.addEventListener("mouseleave", () => highlightHotspot(idx, false));

        overlay.appendChild(itemEl);
      });
    }

    // Render defined hotspots list cards below canvas (sleek, compact rows)
    function renderHotspotsList() {
      if (!hotspotsList) return;
      hotspotsList.innerHTML = "";

      if (hotspots.length === 0) {
        hotspotsList.innerHTML = `
          <div class="text-center p-3 text-muted border border-dashed rounded bg-light font-monospace small">
            <i class="fas fa-hand-pointer me-1"></i> No targets defined yet. Drag on the image above to define suspicious areas.
          </div>
        `;
        return;
      }

      hotspots.forEach((spot, idx) => {
        const isBox = spot.x_min !== undefined && spot.x_max !== undefined;
        const rowEl = document.createElement("div");
        rowEl.className = "card border shadow-sm rfh-hotspot-row";
        rowEl.setAttribute("data-card-idx", idx);
        rowEl.style.transition = "all 0.15s ease";

        const coordsBadge = isBox
          ? `Box: X ${spot.x_min}%–${spot.x_max}% | Y ${spot.y_min}%–${spot.y_max}%`
          : `Circle: (${spot.x}%, ${spot.y}%) | R: ${spot.radius || 8}%`;

        const sizeTag = isBox
          ? `${spot.w}% × ${spot.h}%`
          : `R: ${spot.radius || 8}%`;

        rowEl.innerHTML = `
          <div class="card-body p-2 d-flex flex-wrap align-items-center gap-2">
            <div class="d-flex align-items-center gap-1 flex-shrink-0" style="min-width: 120px;">
              <span class="badge ${isBox ? 'bg-success' : 'bg-danger'} font-monospace">
                #${idx + 1} ${isBox ? 'BOX' : 'CIRCLE'}
              </span>
              <span class="badge bg-light text-secondary border font-monospace small" title="${coordsBadge}">
                ${sizeTag}
              </span>
            </div>
            <div class="flex-grow-1" style="min-width: 150px;">
              <input type="text" class="form-control form-control-sm rfh-label-input font-monospace" value="${escapeAttr(spot.label || '')}" placeholder="Label: e.g. Deceptive URL Domain">
            </div>
            <div class="flex-grow-1" style="min-width: 200px;">
              <input type="text" class="form-control form-control-sm rfh-expl-input small" value="${escapeAttr(spot.explanation || '')}" placeholder="Finding: why is this suspicious?">
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger py-1 px-2 flex-shrink-0 rfh-card-del-btn" title="Delete target">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        `;

        const labelInput = rowEl.querySelector(".rfh-label-input");
        const explInput = rowEl.querySelector(".rfh-expl-input");
        const delBtn = rowEl.querySelector(".rfh-card-del-btn");

        if (labelInput) {
          labelInput.addEventListener("input", () => {
            spot.label = labelInput.value.trim() || `Target #${idx + 1}`;
            syncTextareaOnly();
            const targetOverlay = overlay.querySelector(`[data-spot-idx="${idx}"] .rfh-target-label-text`);
            if (targetOverlay) targetOverlay.textContent = spot.label;
          });
        }

        if (explInput) {
          explInput.addEventListener("input", () => {
            spot.explanation = explInput.value.trim();
            syncTextareaOnly();
          });
        }

        if (delBtn) {
          delBtn.addEventListener("click", () => deleteHotspot(idx));
        }

        rowEl.addEventListener("mouseenter", () => highlightHotspot(idx, true));
        rowEl.addEventListener("mouseleave", () => highlightHotspot(idx, false));

        hotspotsList.appendChild(rowEl);
      });
    }

    function syncTextareaOnly() {
      if (hotspotsJsonArea) {
        hotspotsJsonArea.value = JSON.stringify(hotspots, null, 2);
      }
    }

    function deleteHotspot(index) {
      hotspots.splice(index, 1);
      syncState();
    }

    function highlightHotspot(index, active) {
      const targetOverlay = overlay ? overlay.querySelector(`[data-spot-idx="${index}"]`) : null;
      const card = hotspotsList ? hotspotsList.querySelector(`[data-card-idx="${index}"]`) : null;

      if (targetOverlay) {
        if (active) {
          targetOverlay.style.boxShadow = "0 0 25px #00ff88, 0 0 10px #ffffff";
          targetOverlay.style.zIndex = "50";
        } else {
          targetOverlay.style.boxShadow = "";
          targetOverlay.style.zIndex = "";
        }
      }
      if (card) {
        if (active) {
          card.classList.add("border-primary", "shadow");
        } else {
          card.classList.remove("border-primary", "shadow");
        }
      }
    }

    if (clearAllBtn) {
      clearAllBtn.addEventListener("click", () => {
        if (hotspots.length === 0) return;
        if (confirm("Are you sure you want to remove all defined hotspot targets?")) {
          hotspots = [];
          syncState();
        }
      });
    }

    // Add Box Hotspot
    function addBoxHotspot(x, y, w, h, xMin, xMax, yMin, yMax) {
      const idx = hotspots.length + 1;
      hotspots.push({
        id: "hs_" + Date.now().toString(36),
        label: `Red Flag #${idx}`,
        explanation: "",
        x: x,
        y: y,
        w: w,
        h: h,
        x_min: xMin,
        x_max: xMax,
        y_min: yMin,
        y_max: yMax,
        radius: Math.max(w, h) / 2
      });
      syncState();
    }

    // Add Point Hotspot
    function addPointHotspot(x, y) {
      const idx = hotspots.length + 1;
      const radius = 8.0;
      hotspots.push({
        id: "hs_" + Date.now().toString(36),
        label: `Red Flag #${idx}`,
        explanation: "",
        x: Number(x.toFixed(1)),
        y: Number(y.toFixed(1)),
        radius: radius
      });
      syncState();
    }

    // Canvas Mouse Event Handlers for Dragging Box / Clicking Point
    if (canvasInner && previewImg) {
      canvasInner.addEventListener("mousedown", (e) => {
        if (e.target.closest(".rfh-del-btn") || e.target.closest("button")) return;
        const rect = previewImg.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        startX = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
        startY = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));
        isDragging = true;

        if (currentMode === "box" && dragBox) {
          dragBox.style.left = `${startX}%`;
          dragBox.style.top = `${startY}%`;
          dragBox.style.width = "0%";
          dragBox.style.height = "0%";
          dragBox.classList.remove("d-none");
        }
      });

      window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const rect = previewImg.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const curX = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
        const curY = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));

        if (currentMode === "box" && dragBox) {
          const l = Math.min(startX, curX);
          const t = Math.min(startY, curY);
          const w = Math.abs(curX - startX);
          const h = Math.abs(curY - startY);

          dragBox.style.left = `${l}%`;
          dragBox.style.top = `${t}%`;
          dragBox.style.width = `${w}%`;
          dragBox.style.height = `${h}%`;
        }
      });

      window.addEventListener("mouseup", (e) => {
        if (!isDragging) return;
        isDragging = false;
        if (dragBox) dragBox.classList.add("d-none");

        const rect = previewImg.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const endX = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
        const endY = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));

        const w = Math.abs(endX - startX);
        const h = Math.abs(endY - startY);

        if (currentMode === "box") {
          if (w < 1.5 && h < 1.5) {
            addPointHotspot(startX, startY);
          } else {
            const xMin = Number(Math.min(startX, endX).toFixed(1));
            const xMax = Number(Math.max(startX, endX).toFixed(1));
            const yMin = Number(Math.min(startY, endY).toFixed(1));
            const yMax = Number(Math.max(startY, endY).toFixed(1));
            const boxW = Number((xMax - xMin).toFixed(1));
            const boxH = Number((yMax - yMin).toFixed(1));
            const cx = Number(((xMin + xMax) / 2).toFixed(1));
            const cy = Number(((yMin + yMax) / 2).toFixed(1));

            addBoxHotspot(cx, cy, boxW, boxH, xMin, xMax, yMin, yMax);
          }
        } else {
          addPointHotspot(startX, startY);
        }
      });
    }

    // Image Loader
    function updateMediaBar(url) {
      if (mediaBar) {
        if (url && url.trim()) {
          mediaBar.classList.remove("d-none");
          if (dropzone) dropzone.classList.add("d-none");
          if (mediaThumb) mediaThumb.src = url.trim();
          if (mediaName) mediaName.textContent = url.trim().split("/").pop() || url.trim();
        } else {
          mediaBar.classList.add("d-none");
          if (dropzone) dropzone.classList.remove("d-none");
        }
      }
    }

    function loadImage(url) {
      if (!url || !url.trim()) {
        if (canvasEmpty) canvasEmpty.classList.remove("d-none");
        if (canvasInner) canvasInner.classList.add("d-none");
        updateMediaBar("");
        return;
      }
      const cleanUrl = url.trim();
      previewImg.src = cleanUrl;
      previewImg.onload = () => {
        if (canvasEmpty) canvasEmpty.classList.add("d-none");
        if (canvasInner) canvasInner.classList.remove("d-none");
        updateMediaBar(cleanUrl);
        renderHotspotsOnCanvas();
      };
      previewImg.onerror = () => {
        if (canvasEmpty) canvasEmpty.classList.remove("d-none");
        if (canvasInner) canvasInner.classList.add("d-none");
        updateMediaBar("");
      };
    }

    if (imageUrlInput) {
      imageUrlInput.addEventListener("input", () => loadImage(imageUrlInput.value));
      imageUrlInput.addEventListener("change", () => loadImage(imageUrlInput.value));
    }
    if (loadUrlBtn && imageUrlInput) {
      loadUrlBtn.addEventListener("click", () => loadImage(imageUrlInput.value));
    }

    // Toggle URL box
    if (toggleUrlBtn && urlContainer) {
      toggleUrlBtn.addEventListener("click", () => {
        urlContainer.classList.toggle("d-none");
      });
    }

    // File Upload Handler (via CTFd /api/v1/files)
    async function handleFile(file) {
      if (!file) return;

      const blobUrl = URL.createObjectURL(file);
      loadImage(blobUrl);

      if (uploadStatus) {
        uploadStatus.className = "alert alert-warning py-2 small d-flex align-items-center gap-2 mb-3";
        uploadStatus.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Uploading <strong>${escapeHtml(file.name)}</strong> to CTFd server...`;
        uploadStatus.classList.remove("d-none");
      }

      const formData = new FormData();
      formData.append("file", file);
      const csrf = (window.init && window.init.csrfNonce) || (window.CTFd && window.CTFd.config && window.CTFd.config.csrfNonce) || "";
      formData.append("nonce", csrf);

      try {
        const response = await fetch("/api/v1/files", {
          method: "POST",
          headers: {
            "CSRF-Token": csrf
          },
          body: formData
        });
        const data = await response.json();
        if (data.success && data.data && data.data[0]) {
          const fileLoc = data.data[0].location;
          const finalUrl = `/files/${fileLoc}`;
          if (imageUrlInput) {
            imageUrlInput.value = finalUrl;
            imageUrlInput.dispatchEvent(new Event("change", { bubbles: true }));
          }
          updateMediaBar(finalUrl);
          if (uploadStatus) {
            uploadStatus.className = "alert alert-success py-2 small d-flex align-items-center justify-content-between mb-3";
            uploadStatus.innerHTML = `
              <div>
                <i class="fas fa-check-circle text-success me-1"></i>
                <strong>Uploaded:</strong> <span class="font-monospace">${escapeHtml(file.name)}</span> &rarr; <span class="font-monospace fw-bold">${finalUrl}</span>
              </div>
              <button type="button" class="btn-close btn-close-sm" onclick="this.parentElement.classList.add('d-none')"></button>
            `;
          }
        } else {
          if (uploadStatus) {
            uploadStatus.className = "alert alert-danger py-2 small mb-3";
            uploadStatus.innerHTML = `<i class="fas fa-times-circle text-danger me-1"></i> Upload failed: ${data.errors ? JSON.stringify(data.errors) : "Server returned error"}`;
          }
        }
      } catch (err) {
        if (uploadStatus) {
          uploadStatus.className = "alert alert-danger py-2 small mb-3";
          uploadStatus.innerHTML = `<i class="fas fa-times-circle text-danger me-1"></i> Upload failed: ${escapeHtml(err.message)}`;
        }
      }
    }

    if (browseBtn && fileInput) {
      browseBtn.addEventListener("click", () => fileInput.click());
    }
    if (replaceImageBtn && fileInput) {
      replaceImageBtn.addEventListener("click", () => fileInput.click());
    }
    if (dropzone && fileInput) {
      dropzone.addEventListener("click", (e) => {
        if (e.target !== browseBtn) fileInput.click();
      });
      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("border-primary", "bg-white");
      });
      dropzone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        dropzone.classList.remove("border-primary", "bg-white");
      });
      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("border-primary", "bg-white");
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
          handleFile(e.dataTransfer.files[0]);
        }
      });
      fileInput.addEventListener("change", () => {
        if (fileInput.files && fileInput.files.length) {
          handleFile(fileInput.files[0]);
        }
      });
    }

    // Manual edits in raw JSON textarea re-sync to canvas
    if (hotspotsJsonArea) {
      hotspotsJsonArea.addEventListener("change", () => {
        try {
          const parsed = JSON.parse(hotspotsJsonArea.value.trim());
          if (Array.isArray(parsed)) {
            hotspots = parsed;
            const count = hotspots.length;
            if (counterBadge) counterBadge.textContent = `${count} Target${count === 1 ? '' : 's'}`;
            if (listCount) listCount.textContent = count;
            renderHotspotsOnCanvas();
            renderHotspotsList();
          }
        } catch (e) {}
      });
    }

    // Initial render
    syncState();
    if (imageUrlInput && imageUrlInput.value.trim()) {
      loadImage(imageUrlInput.value.trim());
    }

    function escapeHtml(str) {
      const d = document.createElement("div");
      d.textContent = str || "";
      return d.innerHTML;
    }

    function escapeAttr(str) {
      return (str || "").replace(/"/g, "&quot;");
    }
  }

  window.initRedFlagHotspotAdmin = initRedFlagHotspotAdmin;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initRedFlagHotspotAdmin);
  } else {
    setTimeout(initRedFlagHotspotAdmin, 50);
  }
})();
