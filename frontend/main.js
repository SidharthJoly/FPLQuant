import { api } from "./api.js";
import { API_BASE } from "./config.js";
import { loadTicker } from "./ticker.js";

const tabs = document.querySelectorAll(".fq-nav__btn");
const panels = document.querySelectorAll(".panel");
const navSlider = document.getElementById("nav-slider");
const themeToggle = document.getElementById("theme-toggle");
const feedLabel = document.getElementById("feed-label");
const feedNote = document.getElementById("feed-note");

const tickerLoaded = { done: false };

function setActiveTab(target) {
  const index = Array.from(tabs).findIndex((t) => t.dataset.tab === target);
  const tabWidth = tabs[0].getBoundingClientRect().width;
  navSlider.style.transform = `translateX(${index * tabWidth}px)`;

  for (const t of tabs) {
    const active = t.dataset.tab === target;
    t.classList.toggle("active", active);
    t.setAttribute("aria-selected", active ? "true" : "false");
  }
  for (const panel of panels) {
    panel.classList.toggle("active", panel.id === `panel-${target}`);
  }

  if (target === "ticker" && !tickerLoaded.done) {
    tickerLoaded.done = true;
    loadTicker();
  }
}

for (const tab of tabs) {
  tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
}
setActiveTab("optimizer");

window.addEventListener("resize", () => {
  const active = document.querySelector(".fq-nav__btn.active");
  if (active) setActiveTab(active.dataset.tab);
});

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeToggle.classList.toggle("is-light", theme === "light");
}

const savedTheme = localStorage.getItem("fplquant-theme");
applyTheme(savedTheme === "light" ? "light" : "dark");

themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  localStorage.setItem("fplquant-theme", next);
  applyTheme(next);
});

// Backend health probe — purely cosmetic (the "live"/"demo data" pill and
// footer note), every real fetch already handles its own errors.
(async () => {
  try {
    const ctl = new AbortController();
    const timeout = setTimeout(() => ctl.abort(), 3500);
    const res = await fetch(`${API_BASE}/health`, { signal: ctl.signal });
    clearTimeout(timeout);
    if (res.ok) {
      feedLabel.textContent = "live";
      feedNote.textContent = "Connected to the live backend";
    }
  } catch {
    /* stays on the "demo data" default */
  }
})();

// Deadline countdown.
const deadlineValueEl = document.getElementById("deadline-value");
let deadlineMs = null;

api
  .getNextDeadline()
  .then((res) => {
    if (res.deadline) deadlineMs = new Date(res.deadline).getTime();
    else deadlineValueEl.textContent = "Season over";
  })
  .catch(() => {
    deadlineValueEl.textContent = "—";
  });

setInterval(() => {
  if (deadlineMs === null) return;
  const left = Math.max(0, deadlineMs - Date.now());
  const days = Math.floor(left / 86400000);
  const hours = Math.floor(left / 3600000) % 24;
  const mins = Math.floor(left / 60000) % 60;
  const secs = Math.floor(left / 1000) % 60;
  deadlineValueEl.textContent = `${days}d ${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}, 1000);

// Ticker tape — real top price/ownership movers, looped for a seamless scroll.
const tapeTrack = document.getElementById("tape-track");

api
  .getMarketMomentum({ top: 12, lookback: 5 })
  .then((movers) => {
    if (movers.length === 0) return;
    const items = movers.flatMap((m) => [
      tapeItem(m.web_name, "price", m.price_change / 10, (v) => `£${Math.abs(v).toFixed(1)}m`),
      tapeItem(m.web_name, "owned", m.ownership_change_pct * 100, (v) => `${Math.abs(v).toFixed(1)}%`),
    ]);
    // Duplicated so the 50%-translate loop (see .fq-tape keyframe) is seamless.
    for (const item of [...items, ...items]) tapeTrack.appendChild(item);
  })
  .catch(() => {});

function tapeItem(name, kind, delta, format) {
  const up = delta >= 0;
  const el = document.createElement("div");
  el.className = "fq-tape-item";

  const nameEl = document.createElement("span");
  nameEl.className = "fq-tape-item__name";
  nameEl.textContent = name;

  const kindEl = document.createElement("span");
  kindEl.className = "fq-tape-item__kind";
  kindEl.textContent = kind;

  const deltaEl = document.createElement("span");
  deltaEl.className = "fq-tape-item__delta";
  deltaEl.style.color = up ? "var(--fq-up)" : "var(--fq-down)";
  deltaEl.textContent = `${up ? "▲" : "▼"} ${format(delta)}`;

  el.appendChild(nameEl);
  el.appendChild(kindEl);
  el.appendChild(deltaEl);
  return el;
}

// Hero stats (squad value / XI points / captain) — populated once a squad
// has been built; see optimizer.js's updateHero().
export function updateHero({ value, points, captain }) {
  document.getElementById("hero-value").textContent = value;
  document.getElementById("hero-points").textContent = points;
  document.getElementById("hero-captain").textContent = captain;
}
