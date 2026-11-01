"use strict";

const $ = selector => document.querySelector(selector);
const elements = {
  status: $("#system-status"), mode: $("#mode-badge"), run: $("#run-once"), watch: $("#start-watch"), stop: $("#stop-run"),
  pid: $("#runtime-pid"), start: $("#runtime-start"), exit: $("#runtime-exit"), progress: $("#progress-content"), pulse: $("#pulse-label"),
  inputs: $("#file-list"), inputCount: $("#input-count"), reports: $("#reports"), reportCount: $("#report-count"), log: $("#log-output"),
  form: $("#upload-form"), fileInput: $("#file-input"), selected: $("#selected-files"), dropzone: $("#dropzone"), toast: $("#toast"),
  dialog: $("#report-dialog"), frame: $("#report-frame"), dialogTitle: $("#dialog-title"), openTab: $("#open-tab"),
};
let selectedFiles = [];
let toastTimer;

function escapeHtml(value) { const node = document.createElement("span"); node.textContent = value ?? ""; return node.innerHTML; }
function formatBytes(bytes) { if (bytes < 1024) return `${bytes} B`; if (bytes < 1048576) return `${(bytes/1024).toFixed(1)} KB`; return `${(bytes/1048576).toFixed(1)} MB`; }
function formatDate(value) { return value ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value)) : "—"; }
function shortNumber(value) { return Number.isFinite(Number(value)) ? Number(value).toPrecision(4) : "—"; }
function toast(message, error=false) { clearTimeout(toastTimer); elements.toast.textContent = message; elements.toast.className = error ? "show error" : "show"; toastTimer = setTimeout(() => elements.toast.className = "", 3200); }

async function api(url, options={}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.errors?.join("; ") || "Falha na operação");
  return data;
}

function renderInputs(files) {
  elements.inputCount.textContent = files.length;
  elements.inputs.innerHTML = files.length ? files.slice(0, 8).map(file => `<div class="file-row"><strong>${escapeHtml(file.name)}</strong><span>${formatBytes(file.size)} · ${formatDate(file.modified)}</span></div>`).join("") : "<div class='empty-state'>A pasta de entrada está vazia.</div>";
}

function renderProgress(progress) {
  if (!progress.length) { elements.progress.innerHTML = '<div class="empty-state">Inicie uma execução para acompanhar EIS → DRT → GSF → ESC → Relatório.</div>'; return; }
  const labels = { 1: "EIS", 2: "DRT", 3: "GSF", 4: "ESC", 5: "Relatório" };
  elements.progress.innerHTML = progress.slice(-5).reverse().map(sample => `<article class="sample-progress"><div class="sample-name">${escapeHtml(sample.sample)}</div><div class="agent-track">${[1,2,3,4,5].map(agent => { const state=sample.agents[String(agent)]?.state || "pending"; return `<div class="agent ${state}"><b>${String(agent).padStart(2,"0")} · ${labels[agent]}</b><span>${state === "complete" ? "concluído" : state === "running" ? "processando" : state === "failed" ? "falhou" : "aguardando"}</span></div>`; }).join("")}</div></article>`).join("");
}

function renderReports(reports) {
  elements.reportCount.textContent = reports.length;
  if (!reports.length) { elements.reports.innerHTML = '<div class="empty-state">Nenhum relatório gerado.</div>'; return; }
  elements.reports.innerHTML = reports.map(report => { const summary=report.summary || {}; return `<article class="report-card"><h4>${escapeHtml(report.sample)}</h4><div class="meta">${formatDate(report.modified)} · ${formatBytes(report.size)}</div><div class="report-kpis"><div><b>${shortNumber(summary.R_ct)}</b><span>Rct / Ω</span></div><div><b>${shortNumber(summary.alpha_mean)}</b><span>α médio</span></div><div><b>${shortNumber(summary.I_crit)}</b><span>Icrit</span></div></div><div class="report-actions"><button class="button secondary open-report" data-url="${escapeHtml(report.url)}" data-sample="${escapeHtml(report.sample)}">Abrir no painel</button><a class="button ghost" href="${escapeHtml(report.url)}" target="_blank" rel="noopener">Nova aba</a></div></article>`; }).join("");
}

function renderStatus(state) {
  elements.status.classList.toggle("running", state.running);
  elements.status.querySelector("span:last-child").textContent = state.running ? (state.mode === "watch" ? "Monitoramento ativo" : "Processando") : "Sistema disponível";
  elements.mode.textContent = state.running ? (state.mode === "watch" ? "CONTÍNUO" : "EXECUÇÃO ÚNICA") : "INATIVO";
  elements.mode.classList.toggle("active", state.running); elements.pulse.textContent = state.running ? "Em atividade" : "Aguardando"; elements.pulse.classList.toggle("active", state.running);
  elements.run.disabled = state.running; elements.watch.disabled = state.running; elements.stop.disabled = !state.running;
  elements.pid.textContent = state.pid ?? "—"; elements.start.textContent = formatDate(state.started_at); elements.exit.textContent = state.running ? "—" : (state.exit_code ?? "—");
  renderInputs(state.input_files); renderProgress(state.progress); renderReports(state.reports);
  const nearBottom = elements.log.scrollHeight - elements.log.scrollTop - elements.log.clientHeight < 70;
  elements.log.textContent = state.log || "Aguardando atividade do pipeline…";
  if (nearBottom) elements.log.scrollTop = elements.log.scrollHeight;
}

async function refresh(silent=true) { try { renderStatus(await api("/api/status")); } catch (error) { if (!silent) toast(error.message, true); elements.status.querySelector("span:last-child").textContent = "Sem conexão"; } }
async function action(url, success) { try { renderStatus(await api(url, { method: "POST" })); toast(success); } catch (error) { toast(error.message, true); } }

elements.run.addEventListener("click", () => action("/api/run", "Execução KAIRIS iniciada."));
elements.watch.addEventListener("click", () => action("/api/watch/start", "Monitoramento contínuo iniciado."));
elements.stop.addEventListener("click", () => action("/api/stop", "Execução interrompida."));
$("#refresh").addEventListener("click", () => refresh(false));
elements.fileInput.addEventListener("change", event => { selectedFiles = [...event.target.files]; elements.selected.textContent = selectedFiles.length ? selectedFiles.map(file => file.name).join(" · ") : "Nenhum arquivo selecionado."; });
["dragenter","dragover"].forEach(name => elements.dropzone.addEventListener(name, event => { event.preventDefault(); elements.dropzone.classList.add("dragging"); }));
["dragleave","drop"].forEach(name => elements.dropzone.addEventListener(name, event => { event.preventDefault(); elements.dropzone.classList.remove("dragging"); }));
elements.dropzone.addEventListener("drop", event => { selectedFiles = [...event.dataTransfer.files].filter(file => file.name.toLowerCase().endsWith(".txt")); elements.selected.textContent = selectedFiles.length ? selectedFiles.map(file => file.name).join(" · ") : "Nenhum .txt válido."; });
elements.form.addEventListener("submit", async event => { event.preventDefault(); if (!selectedFiles.length) return toast("Selecione ao menos um arquivo .txt.", true); const body = new FormData(); selectedFiles.forEach(file => body.append("files", file)); try { const result=await api("/api/upload", { method:"POST", body }); selectedFiles=[]; elements.fileInput.value=""; elements.selected.textContent="Nenhum arquivo selecionado."; renderStatus(result.status); toast(`${result.saved.length} arquivo(s) enviado(s).`); } catch(error) { toast(error.message, true); } });
elements.reports.addEventListener("click", event => { const button=event.target.closest(".open-report"); if (!button) return; elements.frame.src=button.dataset.url; elements.openTab.href=button.dataset.url; elements.dialogTitle.textContent=`Relatório KAIRIS · ${button.dataset.sample}`; elements.dialog.showModal(); });
$("#close-dialog").addEventListener("click", () => { elements.dialog.close(); elements.frame.src="about:blank"; });
elements.dialog.addEventListener("click", event => { if (event.target === elements.dialog) { elements.dialog.close(); elements.frame.src="about:blank"; } });

refresh(false);
setInterval(() => refresh(true), 1500);

