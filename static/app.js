const form = document.getElementById("upload-form");
const videoInput = document.getElementById("video");
const selectedFile = document.getElementById("selected-file");
const dropzone = document.querySelector(".dropzone");
const submitBtn = document.getElementById("submit-btn");
const statusPill = document.getElementById("status-pill");
const stageText = document.getElementById("stage-text");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const actions = document.getElementById("actions");
const downloadVideoLink = document.getElementById("download-video-link");
const downloadSrtLink = document.getElementById("download-srt-link");
const logsPanel = document.getElementById("logs-panel");
const logOutput = document.getElementById("log-output");

let activeJobId = null;
let pollTimer = null;

function updateSelectedFileLabel() {
  const file = videoInput.files && videoInput.files[0];
  selectedFile.textContent = file ? file.name : "No file selected";
}

function setStatus(status, message) {
  statusPill.textContent = status[0].toUpperCase() + status.slice(1);
  statusPill.className = `pill ${status}`;
  stageText.textContent = message;
}

function setProgress(value) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0));
  progressBar.style.width = `${clamped}%`;
  progressText.textContent = `${Math.round(clamped)}%`;
}

function setBusy(isBusy) {
  submitBtn.disabled = isBusy;
  submitBtn.textContent = isBusy ? "Processing..." : "Generate captions";
}

function resetDownloadLinks() {
  downloadVideoLink.classList.add("hidden");
  downloadSrtLink.classList.add("hidden");
  downloadVideoLink.removeAttribute("href");
  downloadSrtLink.removeAttribute("href");
}

function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
}

function schedulePoll() {
  stopPolling();
  pollTimer = setTimeout(fetchJobStatus, 2500);
}

async function fetchJobStatus() {
  if (!activeJobId) return;
  try {
    const response = await fetch(`/api/jobs/${activeJobId}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to fetch job status.");
    }

    setStatus(data.status, data.stage || "Working...");
    setProgress(data.progress);

    if (data.log) {
      logsPanel.classList.remove("hidden");
      logOutput.textContent = data.log;
    }

    if (data.status === "completed") {
      setBusy(false);
      actions.classList.remove("hidden");
      resetDownloadLinks();
      if (data.output_video_filename) {
        downloadVideoLink.href = `/api/download/${encodeURIComponent(data.output_video_filename)}`;
        downloadVideoLink.classList.remove("hidden");
      }
      if (data.output_srt_filename) {
        downloadSrtLink.href = `/api/download/${encodeURIComponent(data.output_srt_filename)}`;
        downloadSrtLink.classList.remove("hidden");
      }
      setStatus("completed", "Captioned video ready.");
      stopPolling();
      return;
    }

    if (data.status === "failed") {
      setBusy(false);
      setStatus("failed", data.error || "Job failed.");
      stopPolling();
      return;
    }

    schedulePoll();
  } catch (error) {
    setBusy(false);
    setStatus("failed", error.message);
    stopPolling();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  actions.classList.add("hidden");
  resetDownloadLinks();
  logsPanel.classList.add("hidden");
  logOutput.textContent = "";
  setProgress(0);
  setStatus("running", "Uploading and queuing your video...");
  setBusy(true);

  const formData = new FormData(form);

  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to create job.");
    }

    activeJobId = data.job_id;
    setStatus("running", "Processing started. This can take a while.");
    schedulePoll();
  } catch (error) {
    setBusy(false);
    setStatus("failed", error.message);
  }
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  });
});

videoInput.addEventListener("change", updateSelectedFileLabel);
updateSelectedFileLabel();
