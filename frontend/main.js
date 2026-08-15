import { loadTicker } from "./ticker.js";

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");
const themeToggle = document.getElementById("theme-toggle");

const tickerLoaded = { done: false };

for (const tab of tabs) {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;

    for (const t of tabs) {
      t.classList.toggle("active", t === tab);
      t.setAttribute("aria-selected", t === tab ? "true" : "false");
    }
    for (const panel of panels) {
      panel.classList.toggle("active", panel.id === `panel-${target}`);
    }

    if (target === "ticker" && !tickerLoaded.done) {
      tickerLoaded.done = true;
      loadTicker();
    }
  });
}

function applyTheme(theme) {
  if (theme) {
    document.documentElement.dataset.theme = theme;
  } else {
    delete document.documentElement.dataset.theme;
  }
  themeToggle.textContent = theme === "dark" ? "☀" : "◐";
}

const savedTheme = localStorage.getItem("fplquant-theme");
applyTheme(savedTheme);

themeToggle.addEventListener("click", () => {
  const isDark =
    document.documentElement.dataset.theme === "dark" ||
    (!document.documentElement.dataset.theme &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  const next = isDark ? "light" : "dark";
  localStorage.setItem("fplquant-theme", next);
  applyTheme(next);
});
