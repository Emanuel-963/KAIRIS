"use strict";

const { chromium } = require("playwright");
const path = require("path");
const { browserExecutable } = require("./browser_path");

async function main() {
  const baseUrl = process.argv[2] || "http://127.0.0.1:8765";
  const fixture = path.resolve(process.argv[3] || "tests/fixtures/synthetic_btlab.txt");
  const executablePath = browserExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "KAIRIS", exact: true }).waitFor();
  await page.locator("#file-input").setInputFiles(fixture);
  await page.getByRole("button", { name: "Enviar para o KAIRIS" }).click();
  await page.waitForFunction(() => document.querySelector("#input-count")?.textContent === "1");
  await page.getByRole("button", { name: "Executar uma vez" }).click();
  await page.waitForFunction(() => document.querySelectorAll(".report-card").length === 1, null, { timeout: 60000 });
  await page.waitForFunction(() => [...document.querySelectorAll(".agent")].filter(node => node.classList.contains("complete")).length === 5);
  if (process.argv[4]) await page.screenshot({ path: path.resolve(process.argv[4]), fullPage: true });
  await page.getByRole("button", { name: "Abrir no painel" }).click();
  await page.locator("#report-dialog[open]").waitFor();
  const reportFrame = page.frameLocator("#report-frame");
  await reportFrame.getByRole("heading", { name: /Relatório KAIRIS/ }).waitFor({ timeout: 30000 });
  await page.getByRole("button", { name: "Fechar" }).click();
  await page.getByRole("button", { name: "Iniciar modo contínuo" }).click();
  await page.waitForFunction(() => document.querySelector("#mode-badge")?.textContent === "CONTÍNUO");
  await page.getByRole("button", { name: "Interromper execução" }).click();
  await page.waitForFunction(() => document.querySelector("#mode-badge")?.textContent === "INATIVO");
  if (errors.length) throw new Error(`Erros JavaScript: ${errors.join(" | ")}`);
  console.log("KAIRIS_DASHBOARD_BROWSER_OK");
  await browser.close();
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
