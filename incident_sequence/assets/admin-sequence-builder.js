/**
 * Interactive Visual Sequence & Distractor Builder for CTFd Incident Sequence Plugin
 */
(function () {
  const PRESETS = {
    nist: {
      name: "NIST SP 800-61 Incident Handling Playbook",
      explanation: "Standard NIST SP 800-61 Rev 2 incident handling lifecycle: Preparation, Detection & Analysis, Containment, Forensics, Eradication & Recovery, and Post-Incident Activity. Volatile evidence must be preserved before eradication, and out-of-band communication protects operational security.",
      steps: [
        {
          id: "nist_step_1",
          order: 1,
          text: "Identify anomaly via SIEM alert and confirm Indicators of Compromise (IOCs).",
          explanation: "Detection & Analysis: Initial alert triage and IOC verification confirms active breach."
        },
        {
          id: "nist_step_2",
          order: 2,
          text: "Isolate compromised host from enterprise network to prevent lateral movement.",
          explanation: "Containment: Rapid network segregation halts adversary pivot to domain resources."
        },
        {
          id: "nist_step_3",
          order: 3,
          text: "Capture volatile RAM image and active process artifacts prior to powering down.",
          explanation: "Forensic Preservation: Memory dumps capture transient malware and encryption keys in RAM."
        },
        {
          id: "nist_step_4",
          order: 4,
          text: "Acquire dead-box bitstream disk image of the isolated endpoint.",
          explanation: "Disk Forensics: Bit-for-bit raw disk copy preserves filesystem timestamps and unallocated space."
        },
        {
          id: "nist_step_5",
          order: 5,
          text: "Eradicate malware persistence, rotate compromised credentials, and restore from golden image.",
          explanation: "Eradication & Recovery: Safely sanitize environment and restore verified production services."
        },
        {
          id: "nist_step_6",
          order: 6,
          text: "Conduct post-incident review meeting and update detection rules and playbooks.",
          explanation: "Post-Incident Activity: Lessons learned improve defensive posture against recurring threats."
        }
      ],
      distractors: [
        {
          id: "nist_dist_1",
          text: "Immediately reboot or power-cycle the compromised endpoint to terminate malware.",
          explanation: "Rebooting destroys volatile RAM evidence, active network connections, and transient injected code."
        },
        {
          id: "nist_dist_2",
          text: "Email the adversary directly using contact details found in ransom notes.",
          explanation: "Direct adversary contact violates corporate policy and alerts attackers to containment operations."
        },
        {
          id: "nist_dist_3",
          text: "Post indicators and internal logs to public threat forums before containment.",
          explanation: "Publicly leaking IOCs tips off the adversary and violates non-disclosure and privacy regulations."
        }
      ]
    },
    sans: {
      name: "SANS 6-Step Incident Handling",
      explanation: "Classic SANS PICERL framework: Preparation -> Identification -> Containment -> Eradication -> Recovery -> Lessons Learned.",
      steps: [
        {
          id: "sans_step_1",
          order: 1,
          text: "Preparation: Verify logging health, response toolkits, and communication channels.",
          explanation: "Ensure responders have tools and authorization ready before triage begins."
        },
        {
          id: "sans_step_2",
          order: 2,
          text: "Identification: Triage alerts to determine incident scope, severity, and impacted assets.",
          explanation: "Confirm whether an event constitutes an active security incident."
        },
        {
          id: "sans_step_3",
          order: 3,
          text: "Containment: Apply short-term network isolation followed by long-term system segmentation.",
          explanation: "Limit damage and prevent lateral traversal while keeping systems available for triage."
        },
        {
          id: "sans_step_4",
          order: 4,
          text: "Eradication: Remove rootkits, delete malicious scheduled tasks, and remediate vulnerabilities.",
          explanation: "Thoroughly eliminate all adversary footholds before returning systems to operation."
        },
        {
          id: "sans_step_5",
          order: 5,
          text: "Recovery: Bring cleaned systems back into production with heightened monitoring.",
          explanation: "Return to business operations safely while watching for persistence triggers."
        },
        {
          id: "sans_step_6",
          order: 6,
          text: "Lessons Learned: Document root causes and integrate indicators into automated SIEM rules.",
          explanation: "Feed incident findings back into defense-in-depth controls."
        }
      ],
      distractors: [
        {
          id: "sans_dist_1",
          text: "Purge older log files to free up disk space on the compromised domain controller.",
          explanation: "Purging logs permanently deletes historical audit trails needed for root-cause forensic analysis."
        },
        {
          id: "sans_dist_2",
          text: "Skip containment and immediately patch vulnerabilities on production servers without isolation.",
          explanation: "Patching while an adversary has active command-and-control can trigger wiper logic or retaliatory attacks."
        }
      ]
    },
    ransomware: {
      name: "Ransomware Rapid Containment",
      explanation: "Critical actions during an active ransomware outbreak. Speed in network segregation and backup verification is paramount.",
      steps: [
        {
          id: "rw_step_1",
          order: 1,
          text: "Sever network connection (pull ethernet cable / disable Wi-Fi) on encrypting host immediately.",
          explanation: "Physical or logical network severance halts network share traversal and C2 encryption key exchanges."
        },
        {
          id: "rw_step_2",
          order: 2,
          text: "Audit active network file shares and revoke SMB write permissions across file servers.",
          explanation: "Revoking write permissions halts encryption propagation across shared corporate drives."
        },
        {
          id: "rw_step_3",
          order: 3,
          text: "Identify ransomware variant and look for decryptors or key remnants in memory.",
          explanation: "Identifying the strain determines whether ransom payment is avoidable via known decryptors."
        },
        {
          id: "rw_step_4",
          order: 4,
          text: "Verify offline and immutable backup integrity before initiating any restore process.",
          explanation: "Ensures backups were not wiped or encrypted prior to restoring operational data."
        },
        {
          id: "rw_step_5",
          order: 5,
          text: "Re-image affected workstations and servers from clean baseline images.",
          explanation: "Re-imaging guarantees clean binaries rather than attempting piecemeal file disinfection."
        },
        {
          id: "rw_step_6",
          order: 6,
          text: "Restore sanitized data from verified offline backup and enforce credential resets.",
          explanation: "Complete recovery requires both clean data restoration and credential invalidation."
        }
      ],
      distractors: [
        {
          id: "rw_dist_1",
          text: "Pay ransom via cryptocurrency immediately using company corporate credit cards.",
          explanation: "Paying ransoms does not guarantee decryption, funds criminal enterprise, and may violate legal sanctions."
        },
        {
          id: "rw_dist_2",
          text: "Connect external USB backup drive to infected server to copy remaining unencrypted files.",
          explanation: "Connecting backup media directly to an infected host risks encrypting the backup repository."
        }
      ]
    }
  };

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  function initSequenceBuilder() {
    const stepsTextarea = document.querySelector('textarea[name="steps_json"]');
    const distTextarea = document.querySelector('textarea[name="distractors_json"]');
    const allowDistSwitch = document.querySelector('input[name="allow_distractor_bin"]');
    const explTextarea = document.querySelector('textarea[name="explanation"]');
    const mountPoint = document.getElementById("visual-sequence-builder-root");

    if (!stepsTextarea || !distTextarea || !mountPoint) {
      return;
    }

    let steps = [];
    let distractors = [];

    try {
      steps = JSON.parse(stepsTextarea.value || "[]");
      if (!Array.isArray(steps)) steps = [];
    } catch (e) {
      steps = [];
    }

    try {
      distractors = JSON.parse(distTextarea.value || "[]");
      if (!Array.isArray(distractors)) distractors = [];
    } catch (e) {
      distractors = [];
    }

    // If both empty and on create page, default to NIST preset
    if (steps.length === 0 && distractors.length === 0) {
      steps = JSON.parse(JSON.stringify(PRESETS.nist.steps));
      distractors = JSON.parse(JSON.stringify(PRESETS.nist.distractors));
      if (explTextarea && !explTextarea.value.trim()) {
        explTextarea.value = PRESETS.nist.explanation;
      }
    }

    let isWidescreen = false;

    function syncToJson() {
      // Re-index steps
      steps.forEach((s, idx) => {
        s.order = idx + 1;
        if (!s.id) s.id = `step_${idx + 1}`;
      });

      distractors.forEach((d, idx) => {
        if (!d.id) d.id = `dist_${idx + 1}`;
      });

      stepsTextarea.value = JSON.stringify(steps, null, 2);
      distTextarea.value = JSON.stringify(distractors, null, 2);
    }

    function renderBuilder() {
      syncToJson();

      mountPoint.innerHTML = `
        <div class="card border-primary border-opacity-25 shadow-sm mb-4">
          <!-- Toolbar -->
          <div class="card-header bg-body-tertiary d-flex justify-content-between align-items-center flex-wrap gap-2 py-2 px-3">
            <div class="d-flex align-items-center gap-2">
              <span class="badge bg-primary"><i class="fas fa-sitemap me-1"></i> VISUAL BUILDER</span>
              <strong class="text-body small">Interactive Incident Sequence &amp; Distractor Builder</strong>
            </div>
            <div class="d-flex align-items-center gap-2 flex-wrap">
              <div class="input-group input-group-sm" style="width: auto;">
                <label class="input-group-text bg-body small" for="seq-builder-preset"><i class="fas fa-magic me-1"></i>Preset</label>
                <select class="form-select form-select-sm" id="seq-builder-preset" style="max-width: 220px;">
                  <option value="nist">NIST SP 800-61 (6 Steps)</option>
                  <option value="sans">SANS 6-Step PICERL</option>
                  <option value="ransomware">Ransomware Containment</option>
                  <option value="clear">Clear All (Start Fresh)</option>
                </select>
                <button type="button" class="btn btn-sm btn-outline-primary" id="btn-apply-preset">Load</button>
              </div>
              <button type="button" class="btn btn-sm btn-outline-secondary" id="btn-toggle-widescreen" title="Toggle wide layout">
                <i class="fas fa-arrows-left-right me-1"></i>${isWidescreen ? "Standard Width" : "Widescreen"}
              </button>
            </div>
          </div>

          <div class="card-body p-3">
            <div class="row g-3">
              <!-- Left: Timeline Steps -->
              <div class="col-lg-7">
                <div class="card h-100 border-secondary border-opacity-25">
                  <div class="card-header py-2 px-3 bg-body-tertiary d-flex justify-content-between align-items-center border-bottom border-secondary border-opacity-25">
                    <div>
                      <strong class="text-success small font-monospace"><i class="fas fa-arrow-down-1-9 me-1"></i> TIMELINE STEPS (EXECUTION ORDER)</strong>
                      <div class="text-muted small">Arranged in mandatory chronological sequence (1 &rarr; N)</div>
                    </div>
                    <span class="badge bg-success font-monospace" id="seq-step-count-badge">${steps.length} Steps</span>
                  </div>
                  <div class="card-body p-2" id="builder-steps-list" style="max-height: 520px; overflow-y: auto;">
                    ${renderStepsListHtml()}
                  </div>
                  <div class="card-footer p-2 bg-body-tertiary border-top border-secondary border-opacity-25 d-flex justify-content-between align-items-center">
                    <button type="button" class="btn btn-sm btn-success fw-bold" id="btn-add-step">
                      <i class="fas fa-plus me-1"></i> Add Timeline Step
                    </button>
                    <span class="text-muted small">Steps auto-number 1 to ${steps.length}</span>
                  </div>
                </div>
              </div>

              <!-- Right: Distractors / Prohibited Bin -->
              <div class="col-lg-5">
                <div class="card h-100 border border-secondary border-opacity-25 shadow-sm bg-body">
                  <div class="card-header py-2 px-3 bg-body-tertiary d-flex justify-content-between align-items-center border-bottom border-secondary border-opacity-25">
                    <div>
                      <strong class="text-danger small font-monospace"><i class="fas fa-ban me-1"></i> PROHIBITED ACTIONS / DISTRACTORS</strong>
                      <div class="text-muted small">Countermeasures that operatives must reject</div>
                    </div>
                    <span class="badge bg-danger font-monospace" id="seq-dist-count-badge">${distractors.length} Prohibited</span>
                  </div>
                  <div class="card-body p-2" id="builder-dist-list" style="max-height: 520px; overflow-y: auto;">
                    ${renderDistListHtml()}
                  </div>
                  <div class="card-footer p-2 bg-body-tertiary border-top border-secondary border-opacity-25 d-flex justify-content-between align-items-center">
                    <button type="button" class="btn btn-sm btn-outline-danger fw-bold" id="btn-add-dist">
                      <i class="fas fa-plus me-1"></i> Add Prohibited Action
                    </button>
                    <span class="text-muted small">Moves into Distractor Bin</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Advanced Raw JSON Drawer -->
            <details class="mt-3 border rounded p-2 bg-body-tertiary">
              <summary class="cursor-pointer small fw-bold text-muted">
                <i class="fas fa-code me-1"></i> Advanced: Direct JSON View &amp; Import
              </summary>
              <div class="mt-2 pt-2 border-top">
                <p class="small text-muted mb-2">The textareas below are automatically kept in sync with the visual cards above. You can also paste raw JSON here and click "Reload from JSON".</p>
                <div class="d-flex justify-content-end mb-2">
                  <button type="button" class="btn btn-sm btn-secondary" id="btn-sync-from-json">
                    <i class="fas fa-rotate me-1"></i> Reload Builder from JSON Below
                  </button>
                </div>
              </div>
            </details>
          </div>
        </div>
      `;

      bindBuilderEvents();
    }

    function renderStepsListHtml() {
      if (steps.length === 0) {
        return `
          <div class="text-center text-muted p-4 border border-dashed rounded">
            No steps configured.<br>Click <strong>+ Add Timeline Step</strong> or choose a preset above.
          </div>
        `;
      }

      return steps
        .map((s, idx) => {
          const moveUpDisabled = idx === 0 ? "disabled" : "";
          const moveDownDisabled = idx === steps.length - 1 ? "disabled" : "";

          return `
            <div class="card mb-2 border border-secondary border-opacity-25 shadow-sm builder-step-card bg-body" data-step-index="${idx}">
              <div class="card-header py-1 px-2 bg-body-tertiary d-flex justify-content-between align-items-center border-bottom border-secondary border-opacity-25">
                <div class="d-flex align-items-center gap-2">
                  <span class="badge bg-success font-monospace">Step #${idx + 1}</span>
                  <span class="badge bg-dark border text-light font-monospace small" style="font-size: 0.7rem;">ID: ${escapeHtml(s.id || `step_${idx + 1}`)}</span>
                </div>
                <div class="d-flex align-items-center gap-1">
                  <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-1 btn-move-step-up" ${moveUpDisabled} title="Move Step Up">
                    <i class="fas fa-chevron-up"></i>
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-1 btn-move-step-down" ${moveDownDisabled} title="Move Step Down">
                    <i class="fas fa-chevron-down"></i>
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-danger py-0 px-2 btn-convert-to-dist" title="Convert to Distractor Action" style="font-size: 0.75rem;">
                    &rarr; Distractor
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-1 text-danger btn-delete-step" title="Delete Step">
                    <i class="fas fa-trash-can"></i>
                  </button>
                </div>
              </div>
              <div class="card-body p-2">
                <div class="mb-2">
                  <label class="form-label small fw-bold mb-1">Step Action / Description <span class="text-danger">*</span></label>
                  <textarea class="form-control form-control-sm step-text-input" rows="2" placeholder="e.g. Isolate compromised host from enterprise network...">${escapeHtml(s.text || s.title || "")}</textarea>
                </div>
                <div>
                  <label class="form-label small text-muted mb-1">Educational Debrief Explanation (Shown after solve)</label>
                  <input type="text" class="form-control form-control-sm step-expl-input" value="${escapeHtml(s.explanation || "")}" placeholder="e.g. Containment: Rapid network segregation prevents lateral traversal.">
                </div>
              </div>
            </div>
          `;
        })
        .join("");
    }

    function renderDistListHtml() {
      if (distractors.length === 0) {
        return `
          <div class="text-center text-muted p-4 border border-dashed rounded bg-body-tertiary">
            No prohibited actions configured.<br>Click <strong>+ Add Prohibited Action</strong> to add distractors.
          </div>
        `;
      }

      return distractors
        .map((d, idx) => {
          return `
            <div class="card mb-2 border border-secondary border-opacity-25 shadow-sm builder-dist-card bg-body" data-dist-index="${idx}">
              <div class="card-header py-1 px-2 bg-body-tertiary d-flex justify-content-between align-items-center border-bottom border-secondary border-opacity-25">
                <div class="d-flex align-items-center gap-2">
                  <span class="badge bg-danger text-uppercase font-monospace" style="font-size: 0.72rem;">PROHIBITED</span>
                  <span class="badge bg-dark border text-light font-monospace small" style="font-size: 0.7rem;">ID: ${escapeHtml(d.id || `dist_${idx + 1}`)}</span>
                </div>
                <div class="d-flex align-items-center gap-1">
                  <button type="button" class="btn btn-sm btn-outline-success py-0 px-2 btn-convert-to-step" title="Convert to Timeline Step" style="font-size: 0.75rem;">
                    &larr; Step
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-1 text-danger btn-delete-dist" title="Delete Prohibited Action">
                    <i class="fas fa-trash-can"></i>
                  </button>
                </div>
              </div>
              <div class="card-body p-2">
                <div class="mb-2">
                  <label class="form-label small fw-bold text-danger mb-1">Prohibited Action Text <span class="text-danger">*</span></label>
                  <textarea class="form-control form-control-sm dist-text-input" rows="2" placeholder="e.g. Immediately reboot the endpoint to clear malware...">${escapeHtml(d.text || d.title || "")}</textarea>
                </div>
                <div>
                  <label class="form-label small text-muted mb-1">Debrief Rationale (Why this is harmful/incorrect)</label>
                  <input type="text" class="form-control form-control-sm dist-expl-input" value="${escapeHtml(d.explanation || "")}" placeholder="e.g. Rebooting destroys volatile RAM evidence and active network sockets.">
                </div>
              </div>
            </div>
          `;
        })
        .join("");
    }

    function bindBuilderEvents() {
      // Step Inputs
      mountPoint.querySelectorAll(".step-text-input").forEach((input) => {
        input.addEventListener("input", (e) => {
          const card = e.target.closest(".builder-step-card");
          const idx = parseInt(card.dataset.stepIndex);
          steps[idx].text = e.target.value;
          syncToJson();
        });
      });

      mountPoint.querySelectorAll(".step-expl-input").forEach((input) => {
        input.addEventListener("input", (e) => {
          const card = e.target.closest(".builder-step-card");
          const idx = parseInt(card.dataset.stepIndex);
          steps[idx].explanation = e.target.value;
          syncToJson();
        });
      });

      // Move Step Up
      mountPoint.querySelectorAll(".btn-move-step-up").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const card = e.target.closest(".builder-step-card");
          const idx = parseInt(card.dataset.stepIndex);
          if (idx > 0) {
            const temp = steps[idx];
            steps[idx] = steps[idx - 1];
            steps[idx - 1] = temp;
            renderBuilder();
          }
        });
      });

      // Move Step Down
      mountPoint.querySelectorAll(".btn-move-step-down").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const card = e.target.closest(".builder-step-card");
          const idx = parseInt(card.dataset.stepIndex);
          if (idx < steps.length - 1) {
            const temp = steps[idx];
            steps[idx] = steps[idx + 1];
            steps[idx + 1] = temp;
            renderBuilder();
          }
        });
      });

      // Convert Step to Distractor
      mountPoint.querySelectorAll(".btn-convert-to-dist").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const card = e.target.closest(".builder-step-card");
          const idx = parseInt(card.dataset.stepIndex);
          const item = steps.splice(idx, 1)[0];
          distractors.push({
            id: `dist_${distractors.length + 1}`,
            text: item.text || item.title || "",
            explanation: item.explanation || ""
          });
          renderBuilder();
        });
      });

      // Delete Step
      mountPoint.querySelectorAll(".btn-delete-step").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const card = e.target.closest(".builder-step-card");
          const idx = parseInt(card.dataset.stepIndex);
          if (confirm("Delete this step from timeline?")) {
            steps.splice(idx, 1);
            renderBuilder();
          }
        });
      });

      // Distractor Inputs
      mountPoint.querySelectorAll(".dist-text-input").forEach((input) => {
        input.addEventListener("input", (e) => {
          const card = e.target.closest(".builder-dist-card");
          const idx = parseInt(card.dataset.distIndex);
          distractors[idx].text = e.target.value;
          syncToJson();
        });
      });

      mountPoint.querySelectorAll(".dist-expl-input").forEach((input) => {
        input.addEventListener("input", (e) => {
          const card = e.target.closest(".builder-dist-card");
          const idx = parseInt(card.dataset.distIndex);
          distractors[idx].explanation = e.target.value;
          syncToJson();
        });
      });

      // Convert Distractor to Step
      mountPoint.querySelectorAll(".btn-convert-to-step").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const card = e.target.closest(".builder-dist-card");
          const idx = parseInt(card.dataset.distIndex);
          const item = distractors.splice(idx, 1)[0];
          steps.push({
            id: `step_${steps.length + 1}`,
            order: steps.length + 1,
            text: item.text || item.title || "",
            explanation: item.explanation || ""
          });
          renderBuilder();
        });
      });

      // Delete Distractor
      mountPoint.querySelectorAll(".btn-delete-dist").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const card = e.target.closest(".builder-dist-card");
          const idx = parseInt(card.dataset.distIndex);
          if (confirm("Delete this prohibited action?")) {
            distractors.splice(idx, 1);
            renderBuilder();
          }
        });
      });

      // Add Step Button
      const addStepBtn = mountPoint.querySelector("#btn-add-step");
      if (addStepBtn) {
        addStepBtn.addEventListener("click", () => {
          steps.push({
            id: `step_${steps.length + 1}`,
            order: steps.length + 1,
            text: "",
            explanation: ""
          });
          renderBuilder();
          // Focus newly added step input
          setTimeout(() => {
            const inputs = mountPoint.querySelectorAll(".step-text-input");
            if (inputs.length > 0) inputs[inputs.length - 1].focus();
          }, 50);
        });
      }

      // Add Distractor Button
      const addDistBtn = mountPoint.querySelector("#btn-add-dist");
      if (addDistBtn) {
        addDistBtn.addEventListener("click", () => {
          distractors.push({
            id: `dist_${distractors.length + 1}`,
            text: "",
            explanation: ""
          });
          renderBuilder();
          // Focus newly added distractor input
          setTimeout(() => {
            const inputs = mountPoint.querySelectorAll(".dist-text-input");
            if (inputs.length > 0) inputs[inputs.length - 1].focus();
          }, 50);
        });
      }

      // Apply Preset Button
      const applyPresetBtn = mountPoint.querySelector("#btn-apply-preset");
      const presetSelect = mountPoint.querySelector("#seq-builder-preset");
      if (applyPresetBtn && presetSelect) {
        applyPresetBtn.addEventListener("click", () => {
          const key = presetSelect.value;
          if (key === "clear") {
            if (confirm("Clear all steps and distractors?")) {
              steps = [];
              distractors = [];
              renderBuilder();
            }
            return;
          }

          const preset = PRESETS[key];
          if (!preset) return;

          if (steps.length > 0 || distractors.length > 0) {
            if (!confirm(`Load "${preset.name}" preset? This will overwrite the current sequence.`)) {
              return;
            }
          }

          steps = JSON.parse(JSON.stringify(preset.steps));
          distractors = JSON.parse(JSON.stringify(preset.distractors));
          if (explTextarea) {
            explTextarea.value = preset.explanation;
          }
          if (allowDistSwitch) {
            allowDistSwitch.checked = true;
          }
          renderBuilder();
        });
      }

      // Toggle Widescreen
      const widescreenBtn = mountPoint.querySelector("#btn-toggle-widescreen");
      if (widescreenBtn) {
        widescreenBtn.addEventListener("click", () => {
          isWidescreen = !isWidescreen;
          const modalDialog = mountPoint.closest(".modal-dialog");
          const formCol = mountPoint.closest(".col-md-6") || mountPoint.closest(".col-lg-6") || mountPoint.closest(".col-sm-8");
          const formContainer = mountPoint.closest(".container") || mountPoint.closest(".container-fluid");

          if (modalDialog) {
            if (isWidescreen) {
              modalDialog.classList.add("modal-fullscreen-lg-down", "modal-xl");
              modalDialog.style.maxWidth = "95vw";
            } else {
              modalDialog.classList.remove("modal-fullscreen-lg-down", "modal-xl");
              modalDialog.style.maxWidth = "";
            }
          }

          if (formCol) {
            if (isWidescreen) {
              formCol.classList.remove("col-md-6", "col-lg-6", "col-sm-8");
              formCol.classList.add("col-12");
            } else {
              formCol.classList.remove("col-12");
              formCol.classList.add("col-md-6");
            }
          }

          renderBuilder();
        });
      }

      // Sync from Raw JSON Button
      const syncFromJsonBtn = mountPoint.querySelector("#btn-sync-from-json");
      if (syncFromJsonBtn) {
        syncFromJsonBtn.addEventListener("click", () => {
          try {
            const parsedSteps = JSON.parse(stepsTextarea.value || "[]");
            const parsedDist = JSON.parse(distTextarea.value || "[]");
            if (Array.isArray(parsedSteps)) steps = parsedSteps;
            if (Array.isArray(parsedDist)) distractors = parsedDist;
            renderBuilder();
          } catch (err) {
            alert("Error parsing raw JSON: " + err.message);
          }
        });
      }
    }

    // Ensure JSON is up-to-date on parent form submit
    const parentForm = mountPoint.closest("form");
    if (parentForm) {
      parentForm.addEventListener("submit", () => {
        syncToJson();
      });
    }

    renderBuilder();
  }

  // Auto-init on DOMContentLoaded or immediate if loaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSequenceBuilder);
  } else {
    setTimeout(initSequenceBuilder, 50);
  }

  window.initSequenceBuilder = initSequenceBuilder;
})();
