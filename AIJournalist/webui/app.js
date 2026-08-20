const ui = {
  form: document.querySelector("#researchForm"),
  researchButton: document.querySelector("#researchButton"),
  dateFields: document.querySelector("#dateFields"),
  intervalFields: document.querySelector("#intervalFields"),
  selectedDate: document.querySelector("#selectedDate"),
  startTime: document.querySelector("#startTime"),
  endTime: document.querySelector("#endTime"),
  maxArticles: document.querySelector("#maxArticles"),
  systemState: document.querySelector("#systemState"),
  configWarning: document.querySelector("#configWarning"),
  timezoneLabel: document.querySelector("#timezoneLabel"),
  modelName: document.querySelector("#modelName"),
  sourceNames: document.querySelector("#sourceNames"),
  siteApi: document.querySelector("#siteApi"),
  emptyActivity: document.querySelector("#emptyActivity"),
  jobActivity: document.querySelector("#jobActivity"),
  jobState: document.querySelector("#jobState"),
  jobStage: document.querySelector("#jobStage"),
  jobRange: document.querySelector("#jobRange"),
  progressBar: document.querySelector("#progressBar"),
  readyCount: document.querySelector("#readyCount"),
  processedCount: document.querySelector("#processedCount"),
  skippedCount: document.querySelector("#skippedCount"),
  failedCount: document.querySelector("#failedCount"),
  jobError: document.querySelector("#jobError"),
  cancelButton: document.querySelector("#cancelButton"),
  emptyResults: document.querySelector("#emptyResults"),
  articleList: document.querySelector("#articleList"),
  selectionCount: document.querySelector("#selectionCount"),
  publishBar: document.querySelector("#publishBar"),
  publishStatus: document.querySelector("#publishStatus"),
  publishButton: document.querySelector("#publishButton"),
  toggleLogs: document.querySelector("#toggleLogs"),
  logList: document.querySelector("#logList"),
  toast: document.querySelector("#toast"),
};

let config = null;
let currentJob = null;
let pollTimer = null;
let selectedIds = new Set();
let knownIds = new Set();
let toastTimer = null;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[char]);
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? escapeHtml(url.href) : "#";
  } catch { return "#"; }
}

function showToast(message, error = false) {
  clearTimeout(toastTimer);
  ui.toast.textContent = message;
  ui.toast.className = `toast is-visible${error ? " is-error" : ""}`;
  toastTimer = setTimeout(() => { ui.toast.className = "toast"; }, 4200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let data = null;
  try { data = await response.json(); } catch { /* empty response */ }
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail) ? detail.map(item => item.msg).join("; ") : detail;
    throw new Error(message || `Request failed (${response.status})`);
  }
  return data;
}

async function loadConfig() {
  try {
    config = await api("/api/config");
    ui.selectedDate.value = config.defaults.date;
    ui.startTime.value = config.defaults.start;
    ui.endTime.value = config.defaults.end;
    ui.maxArticles.value = config.defaults.max_articles;
    ui.timezoneLabel.textContent = `${config.timezone} (IST)`;
    ui.modelName.textContent = config.model;
    ui.sourceNames.textContent = config.sources.join(" + ");
    ui.siteApi.textContent = config.site_api_url;

    const fullyReady = config.openrouter_configured && config.site_credentials_configured;
    ui.systemState.textContent = fullyReady ? "● Ready to research & publish" : "● Setup needs attention";
    ui.systemState.className = `system-state ${fullyReady ? "is-ready" : "is-warning"}`;
    const warnings = [];
    if (!config.openrouter_configured) warnings.push("Add OPENROUTER_API_KEY to .env before researching.");
    if (!config.site_credentials_configured) warnings.push("Add SITE_USERNAME and SITE_PASSWORD to .env before publishing. You can still research and preview.");
    if (warnings.length) {
      ui.configWarning.textContent = warnings.join(" ");
      ui.configWarning.classList.remove("hidden");
    } else {
      ui.configWarning.classList.add("hidden");
    }
  } catch (error) {
    ui.systemState.textContent = "● Dashboard API unavailable";
    ui.systemState.className = "system-state is-warning";
    showToast(error.message, true);
  }
}

document.querySelectorAll('input[name="rangeType"]').forEach(input => {
  input.addEventListener("change", () => {
    const isDate = input.value === "date" && input.checked;
    if (!input.checked) return;
    ui.dateFields.classList.toggle("hidden", !isDate);
    ui.intervalFields.classList.toggle("hidden", isDate);
    ui.selectedDate.required = isDate;
    ui.startTime.required = !isDate;
    ui.endTime.required = !isDate;
  });
});

ui.form.addEventListener("submit", async event => {
  event.preventDefault();
  const rangeType = document.querySelector('input[name="rangeType"]:checked').value;
  const payload = {
    range_type: rangeType,
    selected_date: rangeType === "date" ? ui.selectedDate.value : null,
    start: rangeType === "interval" ? ui.startTime.value : null,
    end: rangeType === "interval" ? ui.endTime.value : null,
    max_articles: Number(ui.maxArticles.value),
  };
  ui.researchButton.disabled = true;
  try {
    currentJob = await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
    selectedIds = new Set();
    knownIds = new Set();
    renderJob(currentJob);
    startPolling();
    showToast("Research job started.");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    const active = currentJob && ["QUEUED", "RESEARCHING", "PUBLISHING"].includes(currentJob.state);
    ui.researchButton.disabled = Boolean(active);
  }
});

function startPolling() {
  clearInterval(pollTimer);
  pollTimer = setInterval(refreshJob, 1300);
  refreshJob();
}

async function refreshJob() {
  if (!currentJob) return;
  try {
    currentJob = await api(`/api/jobs/${currentJob.id}`);
    renderJob(currentJob);
    if (!["QUEUED", "RESEARCHING", "PUBLISHING"].includes(currentJob.state)) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  } catch (error) {
    clearInterval(pollTimer);
    showToast(error.message, true);
  }
}

function renderJob(job) {
  ui.emptyActivity.classList.add("hidden");
  ui.jobActivity.classList.remove("hidden");
  ui.jobState.textContent = job.state;
  const stateClass = ["FAILED"].includes(job.state) ? "error" :
    ["READY", "COMPLETE"].includes(job.state) ? "ready" :
    ["QUEUED", "RESEARCHING", "PUBLISHING"].includes(job.state) ? "active" : "idle";
  ui.jobState.className = `state-badge state-badge--${stateClass}`;
  ui.jobStage.textContent = job.stage;
  ui.jobRange.textContent = `${formatDate(job.range.start)} → ${formatDate(job.range.end)}`;
  ui.readyCount.textContent = job.previews.filter(item => item.state === "READY").length;
  ui.processedCount.textContent = job.total ? Math.min(job.current, job.total) : 0;
  ui.skippedCount.textContent = job.skipped;
  ui.failedCount.textContent = job.failed;

  const active = ["QUEUED", "RESEARCHING", "PUBLISHING"].includes(job.state);
  ui.researchButton.disabled = active;
  ui.cancelButton.classList.toggle("hidden", !active);
  if (job.total > 0) {
    ui.progressBar.className = "";
    ui.progressBar.style.width = `${Math.min(100, (job.current / job.total) * 100)}%`;
  } else if (active) {
    ui.progressBar.className = "is-indeterminate";
    ui.progressBar.style.width = "35%";
  } else {
    ui.progressBar.className = "";
    ui.progressBar.style.width = "100%";
  }
  if (job.error) {
    ui.jobError.textContent = job.error;
    ui.jobError.classList.remove("hidden");
  } else {
    ui.jobError.classList.add("hidden");
  }
  renderPreviews(job.previews);
  renderLogs(job.logs);
}

function renderPreviews(previews) {
  ui.emptyResults.classList.toggle("hidden", previews.length > 0);
  for (const preview of previews) {
    if (!knownIds.has(preview.id) && preview.state === "READY") selectedIds.add(preview.id);
    knownIds.add(preview.id);
    if (preview.state !== "READY") selectedIds.delete(preview.id);
  }

  ui.articleList.innerHTML = previews.map(preview => {
    const ready = preview.state === "READY";
    const posted = preview.state === "POSTED";
    const failed = preview.state === "FAILED";
    const stateClass = posted ? "posted" : failed ? "failed" : ready ? "ready" : "";
    const tags = preview.article.tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join("");
    const sourceLink = safeUrl(preview.source.url);
    const imageUrl = safeUrl(preview.source.image_url);
    const fallback = preview.rewrite_mode === "SOURCE_FALLBACK";
    const siteNote = posted ? ` · Site article #${escapeHtml(preview.site_article_id)} (${escapeHtml(preview.site_status)})` : "";
    return `
      <article class="article-card ${posted ? "is-posted" : ""} ${failed ? "is-failed" : ""}">
        <input class="article-check" type="checkbox" data-id="${escapeHtml(preview.id)}"
          ${selectedIds.has(preview.id) ? "checked" : ""} ${ready ? "" : "disabled"}
          aria-label="Select ${escapeHtml(preview.article.title)}">
        <div class="article-main">
          ${imageUrl !== "#" ? `<img class="article-image" src="${imageUrl}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ""}
          <div class="article-meta"><span class="category-chip">${escapeHtml(preview.article.category)}</span>${fallback ? '<span class="fallback-chip">SOURCE EXCERPT · DRAFT ONLY</span>' : ""}<span>${escapeHtml(preview.source.publisher)}</span><span>${escapeHtml(preview.source.extraction_method.replaceAll("_", " "))}</span><span>${escapeHtml(formatDate(preview.source.published_at))}</span></div>
          <h3>${escapeHtml(preview.article.title)}</h3>
          <p class="article-summary">${escapeHtml(preview.article.summary)}</p>
          <p class="article-source">Based on <a href="${sourceLink}" target="_blank" rel="noopener noreferrer">the original report</a>${escapeHtml(siteNote)}</p>
          <div class="tag-list">${tags}</div>
          <div class="article-actions"><details><summary>Read Markdown copy</summary><div class="article-copy">${escapeHtml(preview.article.content_markdown)}</div></details><a class="download-link" href="/api/jobs/${escapeHtml(currentJob.id)}/previews/${escapeHtml(preview.id)}/markdown">Download .md</a></div>
          ${preview.error ? `<p class="article-error">${escapeHtml(preview.error)}</p>` : ""}
        </div>
        <span class="article-state ${stateClass ? `is-${stateClass}` : ""}">${escapeHtml(preview.state)}</span>
      </article>`;
  }).join("");

  document.querySelectorAll(".article-check").forEach(input => {
    input.addEventListener("change", () => {
      input.checked ? selectedIds.add(input.dataset.id) : selectedIds.delete(input.dataset.id);
      updatePublishBar(previews);
    });
  });
  updatePublishBar(previews);
}

function updatePublishBar(previews) {
  const readyIds = new Set(previews.filter(item => item.state === "READY").map(item => item.id));
  selectedIds = new Set([...selectedIds].filter(id => readyIds.has(id)));
  ui.selectionCount.textContent = `${selectedIds.size} selected`;
  const hasReady = readyIds.size > 0;
  ui.publishBar.classList.toggle("hidden", !hasReady);
  ui.publishButton.disabled = selectedIds.size === 0 || !config?.site_credentials_configured || currentJob?.state === "PUBLISHING";
  ui.publishButton.title = config?.site_credentials_configured ? "" : "Add site credentials to .env first";
}

ui.cancelButton.addEventListener("click", async () => {
  if (!currentJob) return;
  ui.cancelButton.disabled = true;
  try {
    currentJob = await api(`/api/jobs/${currentJob.id}/cancel`, { method: "POST" });
    renderJob(currentJob);
    showToast("Cancellation requested.");
  } catch (error) { showToast(error.message, true); }
  finally { ui.cancelButton.disabled = false; }
});

ui.publishButton.addEventListener("click", async () => {
  if (!currentJob || !selectedIds.size) return;
  const status = ui.publishStatus.value;
  if (status === "PUBLISHED" && !window.confirm("Publish selected articles immediately? This bypasses normal editorial review.")) return;
  ui.publishButton.disabled = true;
  try {
    currentJob = await api(`/api/jobs/${currentJob.id}/publish`, {
      method: "POST",
      body: JSON.stringify({ preview_ids: [...selectedIds], status }),
    });
    renderJob(currentJob);
    startPolling();
    showToast(`${selectedIds.size} article(s) queued for the newsroom.`);
  } catch (error) {
    showToast(error.message, true);
    ui.publishButton.disabled = false;
  }
});

function renderLogs(logs) {
  ui.logList.innerHTML = logs.slice().reverse().map(item => `
    <li><time>${escapeHtml(new Date(item.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }))}</time><span>${escapeHtml(item.message)}</span></li>
  `).join("");
}

ui.toggleLogs.addEventListener("click", () => {
  const opening = ui.logList.classList.contains("hidden");
  ui.logList.classList.toggle("hidden", !opening);
  ui.toggleLogs.textContent = opening ? "Hide log" : "Show log";
});

function formatDate(value) {
  const date = new Date(value);
  const options = { dateStyle: "medium", timeStyle: "short" };
  if (config?.timezone) options.timeZone = config.timezone;
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], options);
}

loadConfig();
