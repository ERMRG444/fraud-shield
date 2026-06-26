document.addEventListener("DOMContentLoaded", () => {
    // ----------------------------------------------------
    // SOCKET.IO REAL-TIME ALERTS
    // ----------------------------------------------------
    const socket = io();
    const tickerTextEl = document.getElementById("ticker-text");
    const liveLogListEl = document.getElementById("live-log-list");
    
    socket.on('connect', () => {
        console.log("SocketIO connection established.");
    });
    
    socket.on('new_alert', (data) => {
        // 1. Update Ticker Text
        if (tickerTextEl) {
            tickerTextEl.textContent = `[${data.timestamp}] ${data.message}  •  ${tickerTextEl.textContent.slice(0, 300)}`;
        }
        
        // 2. Prepend to Live Alert Logs list in dashboard
        if (liveLogListEl) {
            const li = document.createElement("li");
            li.className = "p-2 rounded bg-black/30 border border-slate-800 text-xs flex justify-between items-start gap-2 animate-pulse";
            li.innerHTML = `
                <div>
                    <span class="text-rose-500 font-bold">[ALERT]</span> 
                    <span class="text-slate-300">${data.message}</span>
                </div>
                <span class="text-slate-500 font-mono flex-shrink-0">${data.timestamp}</span>
            `;
            liveLogListEl.insertBefore(li, liveLogListEl.firstChild);
            
            // Limit to 10 logs
            if (liveLogListEl.children.length > 10) {
                liveLogListEl.removeChild(liveLogListEl.lastChild);
            }
        }
    });

    // ----------------------------------------------------
    // DASHBOARD TAB CONTROLS
    // ----------------------------------------------------
    const tabs = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;
            
            // Set active class on buttons
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            
            // Set active class on contents
            tabContents.forEach(content => {
                content.classList.remove("active");
                if (content.id === target) {
                    content.classList.add("active");
                }
            });
            
            // Stop webcam stream when navigating away from Currency Authenticator
            if (target !== "currency-tab") {
                stopWebcam();
            }
        });
    });

    // ----------------------------------------------------
    // MODULE 1: COUNTERFEIT CURRENCY DETECTOR
    // ----------------------------------------------------
    const webcamVideo = document.getElementById("webcam-video");
    const webcamCanvas = document.getElementById("webcam-canvas");
    const toggleWebcamBtn = document.getElementById("toggle-webcam-btn");
    const snapFrameBtn = document.getElementById("snap-frame-btn");
    const noteImageUpload = document.getElementById("note-image-upload");
    const uploadSelectBtn = document.getElementById("upload-select-btn");
    const currencyDropArea = document.getElementById("currency-drop-area");
    
    // UI Output elements
    const noteDenomVal = document.getElementById("note-denom-val");
    const noteStatusBadge = document.getElementById("note-status-badge");
    const noteConfidenceVal = document.getElementById("note-confidence-val");
    const noteWarpedImg = document.getElementById("note-warped-img");
    
    // Checkboxes/indicators
    const chkThread = document.getElementById("chk-thread");
    const chkMicroprint = document.getElementById("chk-microprint");
    const chkSerial = document.getElementById("chk-serial");
    const chkColorShift = document.getElementById("chk-color-shift");
    const chkBleed = document.getElementById("chk-bleed");
    
    let webcamStream = null;
    let webcamActive = false;
    let snapInterval = null;

    // Toggle Webcam
    if (toggleWebcamBtn) {
        toggleWebcamBtn.addEventListener("click", async () => {
            if (!webcamActive) {
                try {
                    webcamStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
                    webcamVideo.srcObject = webcamStream;
                    webcamActive = true;
                    toggleWebcamBtn.textContent = "Stop Video Stream";
                    toggleWebcamBtn.classList.remove("btn-primary");
                    toggleWebcamBtn.classList.add("btn-secondary");
                    if (snapFrameBtn) snapFrameBtn.style.display = "inline-flex";
                    
                    // Periodic auto snap scan every 3 seconds for active scanning
                    snapInterval = setInterval(snapFrameAndScan, 3000);
                } catch (err) {
                    console.error("Error opening camera:", err);
                    alert("Webcam permission denied or camera not found.");
                }
            } else {
                stopWebcam();
            }
        });
    }

    function stopWebcam() {
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
        }
        if (webcamVideo) webcamVideo.srcObject = null;
        webcamActive = false;
        if (toggleWebcamBtn) {
            toggleWebcamBtn.textContent = "Start Video Scan";
            toggleWebcamBtn.classList.remove("btn-secondary");
            toggleWebcamBtn.classList.add("btn-primary");
        }
        if (snapFrameBtn) snapFrameBtn.style.display = "none";
        if (snapInterval) clearInterval(snapInterval);
    }

    if (snapFrameBtn) {
        snapFrameBtn.addEventListener("click", snapFrameAndScan);
    }

    function snapFrameAndScan() {
        if (!webcamActive || !webcamVideo || !webcamCanvas) return;
        const ctx = webcamCanvas.getContext("2d");
        webcamCanvas.width = webcamVideo.videoWidth;
        webcamCanvas.height = webcamVideo.videoHeight;
        ctx.drawImage(webcamVideo, 0, 0, webcamCanvas.width, webcamCanvas.height);
        
        const base64Data = webcamCanvas.toDataURL("image/jpeg");
        
        // Show scanning state in UI
        noteDenomVal.textContent = "Scanning frame...";
        noteStatusBadge.textContent = "SCANNING";
        noteStatusBadge.className = "badge bg-blue-500/20 text-blue-400 border border-blue-500/30";
        
        // POST to backend
        fetch("/detect-currency", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ frame: base64Data })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                noteDenomVal.textContent = "Error";
                noteStatusBadge.textContent = "ERROR";
                noteStatusBadge.className = "badge bg-rose-500/20 text-rose-400 border border-rose-500/30";
                return;
            }
            updateCurrencyUI(data);
            refreshStats();
        })
        .catch(err => console.error("Error analyzing frame:", err));
    }

    if (uploadSelectBtn && noteImageUpload) {
        uploadSelectBtn.addEventListener("click", () => {
            noteImageUpload.click();
        });
    }

    if (currencyDropArea && noteImageUpload) {
        // Drag and drop events
        currencyDropArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            currencyDropArea.style.borderColor = "var(--neon-blue)";
        });
        currencyDropArea.addEventListener("dragleave", () => {
            currencyDropArea.style.borderColor = "var(--border-color)";
        });
        currencyDropArea.addEventListener("drop", (e) => {
            e.preventDefault();
            currencyDropArea.style.borderColor = "var(--border-color)";
            if (e.dataTransfer.files.length > 0) {
                noteImageUpload.files = e.dataTransfer.files;
                uploadNoteImage(e.dataTransfer.files[0]);
            }
        });
    }

    if (noteImageUpload) {
        noteImageUpload.addEventListener("change", () => {
            if (noteImageUpload.files.length > 0) {
                uploadNoteImage(noteImageUpload.files[0]);
            }
        });
    }

    function uploadNoteImage(file) {
        const formData = new FormData();
        formData.append("note", file);
        
        // Show loading state in UI
        noteDenomVal.textContent = "Scanning file...";
        noteConfidenceVal.textContent = "0.0%";
        noteStatusBadge.textContent = "SCANNING";
        noteStatusBadge.className = "badge bg-blue-500/20 text-blue-400 border border-blue-500/30";
        
        fetch("/detect-currency", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                noteDenomVal.textContent = "Error";
                noteStatusBadge.textContent = "ERROR";
                noteStatusBadge.className = "badge bg-rose-500/20 text-rose-400 border border-rose-500/30";
                return;
            }
            
            updateCurrencyUI(data);
            refreshStats();
        })
        .catch(err => {
            console.error("Error uploading note:", err);
            noteDenomVal.textContent = "Error";
            noteStatusBadge.textContent = "ERROR";
            noteStatusBadge.className = "badge bg-rose-500/20 text-rose-400 border border-rose-500/30";
        });
    }

    function updateCurrencyUI(data) {
        // 1. Update Header stats
        noteDenomVal.textContent = data.denomination;
        noteConfidenceVal.textContent = `${data.confidence}%`;
        
        // Status Badge styling
        const verdict = data.verdict || data.status;
        noteStatusBadge.textContent = verdict;
        noteStatusBadge.className = "badge";
        if (verdict === "REAL") {
            noteStatusBadge.classList.add("badge-real");
        } else if (verdict.includes("SUSPECTED")) {
            noteStatusBadge.classList.add("badge-suspect");
        } else {
            noteStatusBadge.classList.add("badge-fake");
        }
        
        // 2. Render Checkboxes/indicators
        const setCheckmark = (el, passed, desc) => {
            if (!el) return;
            const check = el.querySelector(".check-icon");
            const detail = el.querySelector(".checklist-desc");
            
            detail.textContent = desc;
            if (passed) {
                check.innerHTML = "✔";
                check.className = "check-icon text-emerald-500 font-bold mr-2";
                el.style.opacity = "1";
            } else {
                check.innerHTML = "✖";
                check.className = "check-icon text-rose-500 font-bold mr-2";
                el.style.opacity = "1";
            }
        };
        
        setCheckmark(chkThread, data.features.security_thread.status === "PASS", data.features.security_thread.details);
        setCheckmark(chkMicroprint, data.features.microprint.status === "PASS", data.features.microprint.details);
        setCheckmark(chkSerial, data.features.serial_number.status === "PASS", data.features.serial_number.details);
        setCheckmark(chkColorShift, data.features.color_shift.status === "PASS", data.features.color_shift.details);
        setCheckmark(chkBleed, data.features.bleed_lines.status === "PASS", data.features.bleed_lines.details);
        
        // 3. Render Output Annotated/Warped Image
        if (noteWarpedImg) {
            noteWarpedImg.src = data.annotated_img;
            noteWarpedImg.style.display = "block";
        }
    }

    // ----------------------------------------------------
    // MODULE 2: DIGITAL ARREST SCAM DETECTOR
    // ----------------------------------------------------
    const scamTextInput = document.getElementById("scam-text-input");
    const scamAudioUpload = document.getElementById("scam-audio-upload");
    const scamDropArea = document.getElementById("scam-drop-area");
    const submitScamBtn = document.getElementById("submit-scam-btn");
    
    // UI Output elements
    const scamRiskVal = document.getElementById("scam-risk-val");
    const scamRiskBar = document.getElementById("scam-risk-bar");
    const scamClassBadge = document.getElementById("scam-class-badge");
    const scamCategoryVal = document.getElementById("scam-category-val");
    const scamTranscriptDisplay = document.getElementById("scam-transcript-display");
    const mhaComplaintText = document.getElementById("mha-complaint-text");
    const downloadComplaintBtn = document.getElementById("download-complaint-btn");

    if (scamDropArea) {
        scamDropArea.addEventListener("click", () => scamAudioUpload.click());
        scamDropArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            scamDropArea.style.borderColor = "var(--neon-blue)";
        });
        scamDropArea.addEventListener("dragleave", () => {
            scamDropArea.style.borderColor = "var(--border-color)";
        });
        scamDropArea.addEventListener("drop", (e) => {
            e.preventDefault();
            scamDropArea.style.borderColor = "var(--border-color)";
            if (e.dataTransfer.files.length > 0) {
                scamAudioUpload.files = e.dataTransfer.files;
                processScamAudio(e.dataTransfer.files[0]);
            }
        });
    }

    if (scamAudioUpload) {
        scamAudioUpload.addEventListener("change", () => {
            if (scamAudioUpload.files.length > 0) {
                processScamAudio(scamAudioUpload.files[0]);
            }
        });
    }

    function processScamAudio(file) {
        const formData = new FormData();
        formData.append("audio", file);
        
        // Show loading states
        scamTranscriptDisplay.innerHTML = `<span class="text-slate-500 font-mono italic animate-pulse">Speech-to-text processing (loading Whisper tiny model, transcribing)...</span>`;
        
        fetch("/classify_scam", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            updateScamUI(data);
            refreshStats();
        })
        .catch(err => {
            console.error("Audio scam processing failed:", err);
            scamTranscriptDisplay.innerHTML = `<span class="text-rose-500 font-mono">Error transcribing audio.</span>`;
        });
    }

    if (submitScamBtn) {
        submitScamBtn.addEventListener("click", () => {
            const text = scamTextInput.value.trim();
            if (!text) {
                alert("Please paste call transcript details first.");
                return;
            }
            
            submitScamBtn.disabled = true;
            submitScamBtn.textContent = "Analyzing transcript...";
            
            const formData = new FormData();
            formData.append("text", text);
            
            fetch("/classify_scam", {
                method: "POST",
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                updateScamUI(data);
                submitScamBtn.disabled = false;
                submitScamBtn.textContent = "Analyze Call Transcript";
                refreshStats();
            })
            .catch(err => {
                console.error("Error analyzing scam text:", err);
                submitScamBtn.disabled = false;
                submitScamBtn.textContent = "Analyze Call Transcript";
            });
        });
    }

    function updateScamUI(data) {
        if (data.error) {
            alert("Analysis failed: " + data.error);
            return;
        }
        
        // 1. Risk Meter
        scamRiskVal.textContent = `${data.risk_score}%`;
        scamRiskBar.style.width = `${data.risk_score}%`;
        
        // Bar color based on risk
        scamRiskBar.className = "h-full rounded-full transition-all duration-500 ";
        if (data.risk_score >= 70) {
            scamRiskBar.classList.add("bg-rose-500");
        } else if (data.risk_score >= 40) {
            scamRiskBar.classList.add("bg-orange-500");
        } else {
            scamRiskBar.classList.add("bg-emerald-500");
        }
        
        // 2. Class Badge
        scamClassBadge.textContent = data.label;
        scamClassBadge.className = "badge";
        if (data.label === "SCAM") {
            scamClassBadge.classList.add("badge-scam");
            scamCategoryVal.textContent = data.category;
            scamCategoryVal.className = "text-rose-500 font-bold";
        } else {
            scamClassBadge.classList.add("badge-legit");
            scamCategoryVal.textContent = "Legitimate Call Details";
            scamCategoryVal.className = "text-emerald-500 font-bold";
        }
        
        // 3. Highlighted Transcript text
        let highlightedText = data.transcript;
        if (data.label === "SCAM" && data.highlighted_phrases && data.highlighted_phrases.length > 0) {
            // Sort keywords by length to prevent nested tag replacement issues
            const sortedPhrases = [...data.highlighted_phrases].sort((a, b) => b.length - a.length);
            
            sortedPhrases.forEach(phrase => {
                const regex = new RegExp(`\\b(${phrase})\\b`, 'gi');
                
                // Categorize phrase to color differently
                const lowerPhrase = phrase.toLowerCase();
                const isAuthority = ["cbi", "customs", "police", "arrest", "warrant", "fir", "jail", "officer", "narcotics"].some(kw => lowerPhrase.includes(kw));
                
                const spanClass = isAuthority ? "scam-highlight-author" : "scam-highlight-threat";
                
                highlightedText = highlightedText.replace(regex, `<span class="${spanClass}">$1</span>`);
            });
        }
        scamTranscriptDisplay.innerHTML = highlightedText;
        
        // 4. MHA complaint draft
        if (data.label === "SCAM" && data.complaint_draft) {
            mhaComplaintText.value = data.complaint_draft;
            downloadComplaintBtn.style.display = "inline-flex";
        } else {
            mhaComplaintText.value = "No complaint draft compiled for legitimate calls.";
            downloadComplaintBtn.style.display = "none";
        }
    }

    if (downloadComplaintBtn) {
        downloadComplaintBtn.addEventListener("click", () => {
            const complaintTxt = mhaComplaintText.value;
            if (!complaintTxt || complaintTxt.startsWith("No complaint")) return;
            
            fetch("/download_scam_pdf", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ complaint_text: complaintTxt })
            })
            .then(res => res.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "MHA_Cybercrime_Complaint.pdf";
                document.body.appendChild(a);
                a.click();
                a.remove();
            })
            .catch(err => console.error("Error downloading PDF:", err));
        });
    }

    // ----------------------------------------------------
    // SCAM CALL SIMULATOR
    // ----------------------------------------------------
    const simCallBtn = document.getElementById("sim-call-btn");
    const simScamType = document.getElementById("sim-scam-type");
    const simStatusBadge = document.getElementById("sim-status-badge");
    const simProgress = document.getElementById("sim-progress");
    const simMetadataPanel = document.getElementById("sim-metadata-panel");
    const simMetadataTable = document.getElementById("sim-metadata-table");
    const simSpoofPanel = document.getElementById("sim-spoof-panel");
    const simSpoofScore = document.getElementById("sim-spoof-score");
    const simSpoofBar = document.getElementById("sim-spoof-bar");
    const simIndicatorsList = document.getElementById("sim-indicators-list");

    function animateStep(stepNum, status) {
        const step = document.getElementById(`sim-step-${stepNum}`);
        if (!step) return;
        const dot = step.querySelector(".sim-step-dot");
        
        if (status === "active") {
            dot.className = "sim-step-dot w-2 h-2 rounded-full bg-blue-500 animate-pulse";
            step.classList.remove("text-slate-500");
            step.classList.add("text-blue-400");
        } else if (status === "done") {
            dot.className = "sim-step-dot w-2 h-2 rounded-full bg-emerald-500";
            step.classList.remove("text-blue-400", "text-slate-500");
            step.classList.add("text-emerald-400");
        } else if (status === "alert") {
            dot.className = "sim-step-dot w-2 h-2 rounded-full bg-rose-500";
            step.classList.remove("text-blue-400", "text-slate-500");
            step.classList.add("text-rose-400");
        }
    }

    function resetSimSteps() {
        for (let i = 1; i <= 8; i++) {
            const step = document.getElementById(`sim-step-${i}`);
            if (step) {
                const dot = step.querySelector(".sim-step-dot");
                dot.className = "sim-step-dot w-2 h-2 rounded-full bg-slate-700";
                step.className = "flex items-center gap-2 text-xs text-slate-500 transition-all";
            }
        }
    }

    if (simCallBtn) {
        simCallBtn.addEventListener("click", async () => {
            const scamType = simScamType.value;
            
            // Disable button
            simCallBtn.disabled = true;
            simCallBtn.innerHTML = `
                <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                Simulating Call...
            `;
            
            // Show progress and reset
            simProgress.classList.remove("hidden");
            simMetadataPanel.classList.add("hidden");
            simSpoofPanel.classList.add("hidden");
            // Hide response action panels
            const raPanels = ["sim-whatsapp-panel", "sim-telecom-panel", "sim-mha-panel"];
            raPanels.forEach(id => { const el = document.getElementById(id); if (el) el.classList.add("hidden"); });
            resetSimSteps();
            
            // Status badge
            simStatusBadge.textContent = "INCOMING";
            simStatusBadge.className = "badge bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 animate-pulse";
            
            // Animate steps with delays for dramatic effect
            animateStep(1, "active");
            await new Promise(r => setTimeout(r, 600));
            animateStep(1, "done");
            
            animateStep(2, "active");
            await new Promise(r => setTimeout(r, 500));
            
            // Fire the actual API call
            try {
                const response = await fetch("/simulate-scam-call", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ scam_type: scamType })
                });
                const data = await response.json();
                
                if (data.error) {
                    simStatusBadge.textContent = "ERROR";
                    simStatusBadge.className = "badge bg-rose-500/20 text-rose-400 border border-rose-500/30";
                    simCallBtn.disabled = false;
                    simCallBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"></path></svg> Simulate Incoming Scam Call`;
                    return;
                }

                animateStep(2, "done");
                
                // Step 3: Spoof detection
                animateStep(3, "active");
                await new Promise(r => setTimeout(r, 500));
                animateStep(3, "done");
                
                // Step 4: NLP classification
                animateStep(4, "active");
                await new Promise(r => setTimeout(r, 400));
                animateStep(4, "done");
                
                // Step 5: WhatsApp Alert
                animateStep(5, "active");
                await new Promise(r => setTimeout(r, 350));
                animateStep(5, "done");
                
                // Step 6: Telecom Flag
                animateStep(6, "active");
                await new Promise(r => setTimeout(r, 350));
                animateStep(6, "done");
                
                // Step 7: MHA Report
                animateStep(7, "active");
                await new Promise(r => setTimeout(r, 350));
                animateStep(7, "done");
                
                // Step 8: All complete
                animateStep(8, "alert");
                await new Promise(r => setTimeout(r, 200));
                
                // Update status badge
                const verdict = data.spoof_analysis.verdict;
                if (verdict.includes("SCAM") || verdict.includes("SPOOF")) {
                    simStatusBadge.textContent = "🚨 " + verdict;
                    simStatusBadge.className = "badge bg-rose-500/20 text-rose-400 border border-rose-500/30";
                } else if (verdict.includes("SUSPICIOUS")) {
                    simStatusBadge.textContent = "⚠ " + verdict;
                    simStatusBadge.className = "badge bg-yellow-500/20 text-yellow-400 border border-yellow-500/30";
                }

                // Populate metadata table
                const meta = data.metadata;
                const metaRows = [
                    ["📞 From Number", meta.from_number, "text-rose-400 font-bold"],
                    ["👤 Caller Name", meta.caller_name, "text-rose-400 font-bold"],
                    ["📡 Carrier", meta.caller_carrier, "text-yellow-400"],
                    ["🌐 Network", meta.caller_network_type, "text-yellow-400"],
                    ["📶 VoIP", meta.is_voip ? "YES ⚠" : "NO", meta.is_voip ? "text-rose-400 font-bold" : "text-emerald-400"],
                    ["🏙 City", meta.caller_city, "text-slate-300"],
                    ["🗺 State", meta.caller_state, "text-slate-300"],
                    ["🌍 Country", `${meta.caller_country_name} (${meta.caller_country})`, "text-rose-400 font-bold"],
                    ["🔒 Encryption", meta.encryption, meta.encryption === "None" ? "text-rose-400" : "text-yellow-400"],
                    ["📱 Target", meta.to_number, "text-emerald-400"],
                    ["📍 Target Location", `${meta.to_city}, ${meta.to_state}`, "text-slate-300"],
                    ["⏱ Duration", `${meta.call_duration_sec}s`, "text-slate-300"],
                ];
                
                simMetadataTable.innerHTML = "";
                metaRows.forEach(([label, value, colorClass]) => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td class="px-2 py-1 text-slate-500 font-medium whitespace-nowrap">${label}</td>
                        <td class="px-2 py-1 ${colorClass} font-mono">${value}</td>
                    `;
                    simMetadataTable.appendChild(tr);
                });
                simMetadataPanel.classList.remove("hidden");

                // Populate spoof indicators
                const spoof = data.spoof_analysis;
                simSpoofScore.textContent = `${spoof.total_risk_score}%`;
                simSpoofBar.style.width = `${spoof.total_risk_score}%`;
                
                simIndicatorsList.innerHTML = "";
                spoof.indicators.forEach(ind => {
                    const sevColor = ind.severity === "CRITICAL" ? "text-rose-500" : 
                                     ind.severity === "HIGH" ? "text-yellow-500" :
                                     ind.severity === "MEDIUM" ? "text-blue-400" : "text-slate-400";
                    const sevIcon = ind.severity === "CRITICAL" ? "🔴" : 
                                    ind.severity === "HIGH" ? "🟡" :
                                    ind.severity === "MEDIUM" ? "🔵" : "⚪";
                    
                    const div = document.createElement("div");
                    div.className = "bg-black/30 border border-slate-800 rounded px-2 py-1.5";
                    div.innerHTML = `
                        <div class="flex items-center justify-between">
                            <span class="${sevColor} text-[11px] font-bold">${sevIcon} ${ind.indicator}</span>
                            <span class="text-rose-400 text-[10px] font-bold">+${ind.risk_delta}%</span>
                        </div>
                        <p class="text-[10px] text-slate-500 mt-0.5">${ind.detail}</p>
                    `;
                    simIndicatorsList.appendChild(div);
                });
                simSpoofPanel.classList.remove("hidden");

                // ---- RESPONSE ACTIONS ----
                if (data.response_actions) {
                    const actions = data.response_actions;

                    // WhatsApp Alert
                    const waPanel = document.getElementById("sim-whatsapp-panel");
                    const waMsg = document.getElementById("sim-whatsapp-msg");
                    const waTo = document.getElementById("sim-wa-to");
                    const waSid = document.getElementById("sim-wa-sid");
                    if (waPanel && actions.whatsapp_alert) {
                        const wa = actions.whatsapp_alert;
                        waMsg.textContent = wa.message_body;
                        waTo.textContent = `To: ${wa.to_number}`;
                        waSid.textContent = `SID: ${wa.message_sid.substring(0, 20)}...`;
                        
                        // Update delivery badge for real vs simulated
                        const waLabel = waPanel.querySelector("span.text-emerald-400.text-xs");
                        const waBadge = waPanel.querySelector("span.bg-emerald-500\\/20");
                        if (wa.real_delivery) {
                            if (waLabel) waLabel.textContent = "📱 Twilio WhatsApp API — LIVE";
                            if (waBadge) { waBadge.textContent = "✓ REAL — DELIVERED"; waBadge.classList.add("animate-pulse"); }
                        } else {
                            if (waBadge) waBadge.textContent = "SIMULATED";
                        }
                        waPanel.classList.remove("hidden");
                    }

                    // Telecom Flag
                    const telPanel = document.getElementById("sim-telecom-panel");
                    const telTable = document.getElementById("sim-telecom-table");
                    const telReqId = document.getElementById("sim-telecom-reqid");
                    const telAction = document.getElementById("sim-telecom-action");
                    if (telPanel && actions.telecom_flag) {
                        const tel = actions.telecom_flag;
                        const rows = [
                            ["Flagged #", tel.payload.flagged_number, "text-rose-400"],
                            ["Origin", `${tel.payload.origin_country_name} (${tel.payload.origin_country})`, "text-yellow-400"],
                            ["Carrier", tel.payload.carrier, "text-slate-300"],
                            ["Risk Score", `${tel.payload.risk_score}%`, "text-rose-400"],
                            ["Action", tel.payload.recommended_action, "text-rose-400 font-bold"],
                            ["Priority", tel.payload.priority, "text-yellow-400"],
                            ["Block Scope", tel.response.block_scope, "text-slate-300"],
                            ["Notified", tel.response.notification_sent_to.join(", "), "text-slate-400"],
                        ];
                        telTable.innerHTML = "";
                        rows.forEach(([k, v, cls]) => {
                            const tr = document.createElement("tr");
                            tr.innerHTML = `<td class="px-1 py-0.5 text-slate-500">${k}</td><td class="px-1 py-0.5 ${cls}">${v}</td>`;
                            telTable.appendChild(tr);
                        });
                        telReqId.textContent = `Request ID: ${tel.request_id}`;
                        telAction.textContent = tel.payload.recommended_action;
                        telPanel.classList.remove("hidden");
                    }

                    // MHA Report
                    const mhaPanel = document.getElementById("sim-mha-panel");
                    const mhaId = document.getElementById("sim-mha-id");
                    const mhaStatus = document.getElementById("sim-mha-status");
                    const mhaLoss = document.getElementById("sim-mha-loss");
                    const mhaSections = document.getElementById("sim-mha-sections");
                    const mhaHash = document.getElementById("sim-mha-hash");
                    const mhaPrevHash = document.getElementById("sim-mha-prev-hash");
                    if (mhaPanel && actions.mha_report) {
                        const mha = actions.mha_report;
                        mhaId.textContent = mha.report_id;
                        mhaStatus.textContent = mha.incident_details.status;
                        mhaLoss.textContent = mha.incident_details.financial_loss;
                        
                        mhaSections.innerHTML = "";
                        mha.legal_sections.forEach(sec => {
                            const d = document.createElement("div");
                            d.className = "flex items-start gap-1";
                            d.innerHTML = `<span class="text-rose-400">▸</span><span class="text-slate-300"><b class="text-rose-400">${sec.section}</b> — ${sec.title}</span>`;
                            mhaSections.appendChild(d);
                        });

                        mhaHash.textContent = mha.evidence_package.chain_hash_sha256;
                        mhaPrevHash.textContent = `Prev: ${mha.evidence_package.previous_chain_hash}`;
                        mhaPanel.classList.remove("hidden");
                    }
                }

                // Feed transcript into the existing scam UI
                const classResult = data.classification;
                classResult.transcript = meta.transcript;
                updateScamUI(classResult);
                
                refreshStats();
                
            } catch (err) {
                console.error("Simulation failed:", err);
                simStatusBadge.textContent = "ERROR";
                simStatusBadge.className = "badge bg-rose-500/20 text-rose-400 border border-rose-500/30";
            }
            
            // Re-enable button
            simCallBtn.disabled = false;
            simCallBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"></path></svg>
                Simulate Incoming Scam Call
            `;
        });
    }

    // ----------------------------------------------------
    // MODULE 3: FRAUD NETWORK GRAPH
    // ----------------------------------------------------
    const csvFileInput = document.getElementById("csv-file-input");
    const graphDropArea = document.getElementById("graph-drop-area");
    const graphIframe = document.getElementById("graph-iframe");
    const accountsTableBody = document.getElementById("accounts-table-body");
    const downloadReportBtn = document.getElementById("download-report-btn");
    
    // Stats elements
    const gStatNodes = document.getElementById("g-stat-nodes");
    const gStatEdges = document.getElementById("g-stat-edges");
    const gStatMules = document.getElementById("g-stat-mules");
    const gStatVolume = document.getElementById("g-stat-volume");

    if (graphDropArea) {
        graphDropArea.addEventListener("click", () => csvFileInput.click());
        graphDropArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            graphDropArea.style.borderColor = "var(--neon-blue)";
        });
        graphDropArea.addEventListener("dragleave", () => {
            graphDropArea.style.borderColor = "var(--border-color)";
        });
        graphDropArea.addEventListener("drop", (e) => {
            e.preventDefault();
            graphDropArea.style.borderColor = "var(--border-color)";
            if (e.dataTransfer.files.length > 0) {
                csvFileInput.files = e.dataTransfer.files;
                uploadTransactionsCSV(e.dataTransfer.files[0]);
            }
        });
    }

    if (csvFileInput) {
        csvFileInput.addEventListener("change", () => {
            if (csvFileInput.files.length > 0) {
                uploadTransactionsCSV(csvFileInput.files[0]);
            }
        });
    }

    function uploadTransactionsCSV(file) {
        const formData = new FormData();
        formData.append("csv_file", file);
        
        gStatNodes.textContent = "Uploading...";
        
        fetch("/visualize_graph", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert("Graph execution error: " + data.error);
                return;
            }
            
            // 1. Refresh IFrame with timestamp to avoid cache
            graphIframe.src = `/static/fraud_graph.html?t=${new Date().getTime()}`;
            
            // 2. Load Graph stats
            gStatNodes.textContent = data.nodes_count;
            gStatEdges.textContent = data.edges_count;
            gStatMules.textContent = data.flagged_count;
            gStatVolume.textContent = `Rs ${data.total_volume.toLocaleString()}`;
            
            // 3. Render accounts table
            accountsTableBody.innerHTML = "";
            data.accounts.forEach(acc => {
                const tr = document.createElement("tr");
                
                // Color code risk label
                let badgeClass = "badge badge-suspect";
                if (acc.risk_score >= 70) badgeClass = "badge badge-fake";
                else if (acc.risk_score < 40) badgeClass = "badge badge-real";
                
                tr.innerHTML = `
                    <td class="font-bold font-mono text-slate-300">#${acc.account_id}</td>
                    <td class="font-bold text-center">${acc.risk_score}%</td>
                    <td><span class="${badgeClass}">${acc.risk_label}</span></td>
                    <td class="text-right font-mono font-medium text-emerald-400">Rs ${acc.in_volume.toLocaleString()}</td>
                    <td class="text-right font-mono font-medium text-rose-400">Rs ${acc.out_volume.toLocaleString()}</td>
                    <td class="text-xs text-slate-400">${acc.reasons}</td>
                `;
                accountsTableBody.appendChild(tr);
            });
            
            // Enable download report button
            downloadReportBtn.style.display = "inline-flex";
            refreshStats();
        })
        .catch(err => {
            console.error("CSV analysis failed:", err);
            gStatNodes.textContent = "Failed";
        });
    }

    // ----------------------------------------------------
    // COMMON: DYNAMIC SUMMARY CARD REFRESH
    // ----------------------------------------------------
    const cardComplaints = document.getElementById("card-complaints");
    const cardFraud = document.getElementById("card-fraud");
    const cardAmount = document.getElementById("card-amount");

    function refreshStats() {
        fetch("/get_dashboard_stats")
        .then(res => res.json())
        .then(data => {
            if (cardComplaints) cardComplaints.textContent = data.complaints_today;
            if (cardFraud) cardFraud.textContent = data.fraud_detected;
            if (cardAmount) cardAmount.textContent = data.amount_protected;
        })
        .catch(err => console.error("Error refreshing dashboard stats:", err));
    }
});
