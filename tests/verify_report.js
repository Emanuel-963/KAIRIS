"use strict";

const { chromium } = require("playwright");
const { pathToFileURL } = require("url");
const path = require("path");
const { browserExecutable } = require("./browser_path");

async function main() {
  const report = process.argv[2];
  if (!report) throw new Error("Usage: node verify_report.js REPORT.html");
  const executablePath = browserExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(pathToFileURL(path.resolve(report)).href, { waitUntil: "networkidle" });
  await page.waitForSelector("#nyquist svg");

  const chartIds = [
    "nyquist", "bode-magnitude", "bode-phase", "drt", "q-map",
    "esc-g1", "esc-g2", "esc-g3", "esc-g4",
  ];
  for (const id of chartIds) {
    const chart = page.locator(`#${id}`);
    if (await chart.locator("svg").count() !== 1) throw new Error(`SVG D3 ausente: ${id}`);
    if (await chart.locator("circle.point").count() < 1) throw new Error(`Pontos ausentes: ${id}`);
    await chart.locator("circle.point").first().dispatchEvent("pointermove", { clientX: 200, clientY: 200 });
    const tooltip = page.locator("#tooltip");
    if (!(await tooltip.isVisible()) || !(await tooltip.textContent()).includes("Hz")) {
      throw new Error(`Tooltip de frequência ausente: ${id}`);
    }
  }
  await page.locator("#drt circle.peak").first().dispatchEvent("pointermove", { clientX: 200, clientY: 200 });
  if (!(await page.locator("#tooltip").textContent()).includes("Área")) {
    throw new Error("Tooltip de pico DRT não contém área integrada");
  }

  const nyquist = page.locator("#nyquist svg");
  const before = await nyquist.locator("path.series-line").getAttribute("d");
  await nyquist.hover({ position: { x: 300, y: 200 } });
  await page.mouse.wheel(0, -600);
  await page.waitForTimeout(150);
  const after = await nyquist.locator("path.series-line").getAttribute("d");
  if (before === after) throw new Error("Zoom do Nyquist não alterou a visualização");
  if (errors.length) throw new Error(`Erros JavaScript: ${errors.join(" | ")}`);
  console.log("KAIRIS_REPORT_BROWSER_OK");
  await browser.close();
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
