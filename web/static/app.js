"use strict";

const $ = selector => document.querySelector(selector);
const elements = {
  status: $("#system-status"), mode: $("#mode-badge"), run: $("#run-once"), watch: $("#start-watch"), stop: $("#stop-run"),
  pid: $("#runtime-pid"), start: $("#runtime-start"), exit: $("#runtime-exit"), update: $("#update-state"), progress: $("#progress-content"), pulse: $("#pulse-label"),
  inputs: $("#file-list"), inputCount: $("#input-count"), reports: $("#reports"), reportCount: $("#report-count"), log: $("#log-output"),
  form: $("#upload-form"), fileInput: $("#file-input"), selected: $("#selected-files"), dropzone: $("#dropzone"), toast: $("#toast"),
  llmToggle: $("#llm-toggle"), llmState: $("#llm-state"),
  dialog: $("#report-dialog"), frame: $("#report-frame"), dialogTitle: $("#dialog-title"), openTab: $("#open-tab"),
  training: $("#training-summary"), dataset: $("#download-dataset"), finetuneReadiness: $("#finetune-readiness"), feedbackDialog: $("#feedback-dialog"), feedbackForm: $("#feedback-form"), feedbackSample: $("#feedback-sample"), correction: $("#feedback-correction"), feedbackNotes: $("#feedback-notes"),
};
let selectedFiles = [];
let toastTimer;

function escapeHtml(value) { const node = document.createElement("span"); node.textContent = value ?? ""; return node.innerHTML; }
function formatBytes(bytes) { if (bytes < 1024) return `${bytes} B`; if (bytes < 1048576) return `${(bytes/1024).toFixed(1)} KB`; return `${(bytes/1048576).toFixed(1)} MB`; }
function formatDate(value) { return value ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value)) : "—"; }
function shortNumber(value) { return Number.isFinite(Number(value)) ? Number(value).toPrecision(4) : "—"; }
function updateLabel(update) { const labels={updated:"Atualizado",up_to_date:"Em dia",update_available:"Disponível",no_remote:"Sem origin",network_error:"Sem rede",local_changes:"Alterações locais",diverged:"Histórico divergente",disabled:"Desativada",not_git_checkout:"Sem Git",update_failed:"Falhou"}; return update ? (labels[update.state] || update.state) : "Não verificada"; }
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
  const feedbackLabels={approved:"Aprovada",corrected:"Corrigida",rejected:"Rejeitada"};
  elements.reports.innerHTML = reports.map(report => { const summary=report.summary || {}; const badge=report.feedback ? `<span class="feedback-badge">${feedbackLabels[report.feedback] || escapeHtml(report.feedback)}</span>` : ""; const approveDisabled=report.has_llm_interpretation ? "" : " disabled title='Sem interpretação da LLM para aprovar'"; return `<article class="report-card"><h4>${escapeHtml(report.sample)}</h4><div class="meta">${formatDate(report.modified)} · ${formatBytes(report.size)}</div>${badge}<div class="report-kpis"><div><b>${shortNumber(summary.R_ct)}</b><span>Rct / Ω</span></div><div><b>${shortNumber(summary.alpha_mean)}</b><span>α médio</span></div><div><b>${shortNumber(summary.I_crit)}</b><span>Icrit</span></div></div><div class="report-actions"><button class="button secondary open-report" data-url="${escapeHtml(report.url)}" data-sample="${escapeHtml(report.sample)}">Abrir no painel</button><a class="button ghost" href="${escapeHtml(report.url)}" target="_blank" rel="noopener">Nova aba</a></div><div class="feedback-actions"><button class="button approve feedback-action" data-verdict="approved" data-sample="${escapeHtml(report.sample)}"${approveDisabled}>✓ Aprovar</button><button class="button secondary feedback-action" data-verdict="corrected" data-sample="${escapeHtml(report.sample)}">✎ Corrigir</button><button class="button reject feedback-action" data-verdict="rejected" data-sample="${escapeHtml(report.sample)}">× Rejeitar</button></div></article>`; }).join("");
}

function renderTraining(training={}) { const examples=training.dataset_examples||0; const minimum=training.finetune_min_validated_examples||50; const values=[training.approved||0,training.corrected||0,training.rejected||0,examples]; [...elements.training.querySelectorAll("b")].forEach((node,index) => node.textContent=values[index]); elements.dataset.classList.toggle("disabled", !examples); elements.finetuneReadiness.textContent=training.finetune_ready ? `Dataset validado pronto para fine-tuning (${examples} exemplos).` : `Aprendizado imediato ativo · ${examples}/${minimum} exemplos para avaliar fine-tuning.`; }

function renderStatus(state) {
  elements.status.classList.toggle("running", state.running);
  elements.status.querySelector("span:last-child").textContent = state.running ? (state.mode === "watch" ? "Monitoramento ativo" : "Processando") : "Sistema disponível";
  elements.mode.textContent = state.running ? (state.mode === "watch" ? "CONTÍNUO" : "EXECUÇÃO ÚNICA") : "INATIVO";
  elements.mode.classList.toggle("active", state.running); elements.pulse.textContent = state.running ? "Em atividade" : "Aguardando"; elements.pulse.classList.toggle("active", state.running);
  elements.run.disabled = state.running; elements.watch.disabled = state.running; elements.stop.disabled = !state.running;
  elements.llmToggle.checked = Boolean(state.llm_enabled); elements.llmState.textContent = state.llm_enabled ? "Ativada · memória persistente" : "Desativada · somente regras";
  elements.pid.textContent = state.pid ?? "—"; elements.start.textContent = formatDate(state.started_at); elements.exit.textContent = state.running ? "—" : (state.exit_code ?? "—");
  elements.update.textContent = updateLabel(state.update);
  renderInputs(state.input_files); renderProgress(state.progress); renderReports(state.reports);
  renderTraining(state.training);
  const nearBottom = elements.log.scrollHeight - elements.log.scrollTop - elements.log.clientHeight < 70;
  elements.log.textContent = state.log || "Aguardando atividade do pipeline…";
  if (nearBottom) elements.log.scrollTop = elements.log.scrollHeight;
}

async function refresh(silent=true) { try { renderStatus(await api("/api/status")); } catch (error) { if (!silent) toast(error.message, true); elements.status.querySelector("span:last-child").textContent = "Sem conexão"; } }
async function action(url, success) { try { renderStatus(await api(url, { method: "POST" })); toast(success); } catch (error) { toast(error.message, true); } }

elements.run.addEventListener("click", () => action("/api/run", "Execução KAIRIS iniciada."));
elements.watch.addEventListener("click", () => action("/api/watch/start", "Monitoramento contínuo iniciado."));
elements.stop.addEventListener("click", () => action("/api/stop", "Execução interrompida."));
elements.llmToggle.addEventListener("change", async event => { const enabled=event.target.checked; try { const state=await api("/api/llm", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({enabled}) }); renderStatus(state); toast(`LLM ${enabled ? "ativada" : "desativada"}.`); } catch(error) { event.target.checked=!enabled; toast(error.message, true); } });
$("#refresh").addEventListener("click", () => refresh(false));
elements.fileInput.addEventListener("change", event => { selectedFiles = [...event.target.files]; elements.selected.textContent = selectedFiles.length ? selectedFiles.map(file => file.name).join(" · ") : "Nenhum arquivo selecionado."; });
["dragenter","dragover"].forEach(name => elements.dropzone.addEventListener(name, event => { event.preventDefault(); elements.dropzone.classList.add("dragging"); }));
["dragleave","drop"].forEach(name => elements.dropzone.addEventListener(name, event => { event.preventDefault(); elements.dropzone.classList.remove("dragging"); }));
elements.dropzone.addEventListener("drop", event => { selectedFiles = [...event.dataTransfer.files].filter(file => [".txt", ".csv"].some(extension => file.name.toLowerCase().endsWith(extension))); elements.selected.textContent = selectedFiles.length ? selectedFiles.map(file => file.name).join(" · ") : "Nenhum TXT ou CSV válido."; });
elements.form.addEventListener("submit", async event => { event.preventDefault(); if (!selectedFiles.length) return toast("Selecione ao menos um arquivo TXT ou CSV.", true); const body = new FormData(); selectedFiles.forEach(file => body.append("files", file)); try { const result=await api("/api/upload", { method:"POST", body }); selectedFiles=[]; elements.fileInput.value=""; elements.selected.textContent="Nenhum arquivo selecionado."; renderStatus(result.status); toast(`${result.saved.length} arquivo(s) enviado(s).`); } catch(error) { toast(error.message, true); } });
async function submitFeedback(sample, verdict, correction="", notes="") { try { const state=await api("/api/feedback", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({sample,verdict,correction,notes}) }); renderStatus(state); toast(verdict === "approved" ? "Interpretação aprovada e dataset atualizado." : verdict === "rejected" ? "Interpretação rejeitada." : "Correção salva e dataset atualizado."); } catch(error) { toast(error.message, true); } }
elements.reports.addEventListener("click", event => { const reportButton=event.target.closest(".open-report"); if (reportButton) { elements.frame.src=reportButton.dataset.url; elements.openTab.href=reportButton.dataset.url; elements.dialogTitle.textContent=`Relatório KAIRIS · ${reportButton.dataset.sample}`; elements.dialog.showModal(); return; } const feedback=event.target.closest(".feedback-action"); if (!feedback || feedback.disabled) return; if (feedback.dataset.verdict === "corrected") { elements.feedbackSample.textContent=feedback.dataset.sample; elements.feedbackDialog.dataset.sample=feedback.dataset.sample; elements.correction.value=""; elements.feedbackNotes.value=""; elements.feedbackDialog.showModal(); elements.correction.focus(); return; } submitFeedback(feedback.dataset.sample, feedback.dataset.verdict); });
$("#close-dialog").addEventListener("click", () => { elements.dialog.close(); elements.frame.src="about:blank"; });
elements.dialog.addEventListener("click", event => { if (event.target === elements.dialog) { elements.dialog.close(); elements.frame.src="about:blank"; } });
function closeFeedback() { elements.feedbackDialog.close(); }
$("#close-feedback").addEventListener("click", closeFeedback); $("#cancel-feedback").addEventListener("click", closeFeedback);
elements.feedbackForm.addEventListener("submit", event => { event.preventDefault(); const sample=elements.feedbackDialog.dataset.sample; const correction=elements.correction.value.trim(); if (!correction) return toast("Escreva a interpretação corrigida.", true); closeFeedback(); submitFeedback(sample, "corrected", correction, elements.feedbackNotes.value.trim()); });

refresh(false);
setInterval(() => refresh(true), 1500);

