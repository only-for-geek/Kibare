"use strict";

// Gestion du theme
const htmlEl = document.documentElement;
const themeToggleBtn = document.getElementById("theme-toggle");

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
