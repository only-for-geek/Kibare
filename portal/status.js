"use strict";

const htmlEl = document.documentElement;
const themeToggleBtn = document.getElementById("theme-toggle");
const statusDot = document.getElementById("status-dot");
const statusLabel = document.getElementById("status-label");

function applyTheme(theme) {
  htmlEl.setAttribute("data-theme", theme);
  try {
    localStorage.setItem("kibare_theme", theme);
  } catch (_) {}
}

const savedTheme = (function () {
  try {
    return localStorage.getItem("kibare_theme") || "dark";
  } catch (_) {
    return "dark";
  }
})();
applyTheme(savedTheme);

if (themeToggleBtn) {
  themeToggleBtn.addEventListener("click", () => {
    const current = htmlEl.getAttribute("data-theme") || "dark";
    applyTheme(current === "dark" ? "light" : "dark");
  });
}

async function checkMatrixAvailability() {
  if (!statusLabel || !statusDot) return;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 4000);

  try {
    const response = await fetch("/health/matrix", {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("Matrix indisponible");
    const data = await response.json();
    if (!Array.isArray(data.versions)) throw new Error("Réponse Matrix invalide");

    statusLabel.textContent = "Serveur en ligne";
    statusDot.className = "status-dot status-online";
  } catch (_) {
    statusLabel.textContent = "Serveur indisponible";
    statusDot.className = "status-dot status-offline";
  } finally {
    window.clearTimeout(timeout);
  }
}

checkMatrixAvailability();
