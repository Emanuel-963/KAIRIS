"use strict";

const fs = require("fs");

function browserExecutable() {
  const platformCandidates = {
    win32: [
      "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ],
    darwin: [
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    linux: [
      "/usr/bin/google-chrome",
      "/usr/bin/google-chrome-stable",
      "/usr/bin/chromium",
      "/usr/bin/chromium-browser",
    ],
  };
  const candidates = [
    process.env.KAIRIS_BROWSER,
    ...(platformCandidates[process.platform] || []),
  ].filter(Boolean);
  return candidates.find(candidate => fs.existsSync(candidate));
}

module.exports = { browserExecutable };
