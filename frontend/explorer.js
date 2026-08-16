import { api } from "./api.js";
import { clear, donutGauge, jerseyIcon } from "./components.js";
import { kitFor } from "./kits.js";

const POSITION_NAMES = { 1: "GKP", 2: "DEF", 3: "MID", 4: "FWD" };
const FDR_COLORS = { 1: "#5fc9a3", 2: "#7cc39a", 3: "#c2b487", 4: "#d69279", 5: "#e0736f" };

const searchInput = document.getElementById("player-search");
const resultsList = document.getElementById("search-results");
const emptyEl = document.getElementById("explorer-empty");
const detailEl = document.getElementById("explorer-detail");
const avatarEl = document.getElementById("player-avatar");
const nameEl = document.getElementById("player-name");
const metaEl = document.getElementById("player-meta");
const trendChartEl = document.getElementById("trend-chart");
const trendSummaryEl = document.getElementById("trend-summary");
const similarGridEl = document.getElementById("similar-grid");
const riskGaugeEl = document.getElementById("risk-gauge");
const gaugeWordEl = document.getElementById("gauge-word");
const gaugeBreakdownEl = document.getElementById("gauge-breakdown");
const fixtureValueEl = document.getElementById("fixture-value");
const fixtureNoteEl = document.getElementById("fixture-note");
const fdrScaleEl = document.getElementById("fdr-scale");
const cheaperOnlyCheckbox = document.getElementById("cheaper-only");
const anyPositionCheckbox = document.getElementById("any-position");

const RECENT_KEY = "fplquant:recentPlayers";
const RECENT_LIMIT = 5;
const POPULAR_LIMIT = 8;

let currentPlayerId = null;
let searchDebounce = null;
let latestSearchQuery = "";
let suggestionsRequestId = 0;

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  const query = searchInput.value.trim();
  latestSearchQuery = query;
  if (query.length === 0) {
    showSuggestions();
    return;
  }
  if (query.length < 2) {
    resultsList.hidden = true;
    return;
  }
  searchDebounce = setTimeout(() => runSearch(query), 150);
});

searchInput.addEventListener("focus", () => {
  const query = searchInput.value.trim();
  if (query.length === 0) showSuggestions();
  else if (query.length >= 2) runSearch(query);
});

document.addEventListener("click", (event) => {
  if (!resultsList.contains(event.target) && event.target !== searchInput) {
    resultsList.hidden = true;
  }
});

function getRecentPlayers() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY)) || [];
  } catch {
    return [];
  }
}

function pushRecentPlayer(player) {
  const entry = {
    id: player.id,
    web_name: player.web_name,
    team_short_name: player.team_short_name,
    element_type: player.element_type,
  };
  const recent = getRecentPlayers().filter((p) => p.id !== entry.id);
  recent.unshift(entry);
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, RECENT_LIMIT)));
}

async function showSuggestions() {
  const requestId = ++suggestionsRequestId;
  clear(resultsList);

  const recent = getRecentPlayers();
  addResultSection("Recent", recent);
  resultsList.hidden = resultsList.children.length === 0;

  const popular = await api.listPlayers({ sort: "popularity", limit: POPULAR_LIMIT });
  const stillRelevant = requestId === suggestionsRequestId && searchInput.value.trim().length === 0;
  if (!stillRelevant) return;

  const recentIds = new Set(recent.map((p) => p.id));
  addResultSection(
    "Popular",
    popular.filter((p) => !recentIds.has(p.id))
  );
  resultsList.hidden = resultsList.children.length === 0;
}

function addResultSection(label, players) {
  if (players.length === 0) return;
  const header = document.createElement("div");
  header.className = "fq-search-header";
  header.textContent = label;
  resultsList.appendChild(header);
  for (const player of players) resultsList.appendChild(resultItem(player));
}

function resultItem(player) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "fq-search-item";
  const name = document.createElement("span");
  name.textContent = player.web_name;
  const meta = document.createElement("span");
  meta.className = "fq-search-item__meta";
  meta.textContent = `${player.team_short_name} · ${POSITION_NAMES[player.element_type]}`;
  btn.appendChild(name);
  btn.appendChild(meta);
  btn.addEventListener("click", () => choosePlayer(player));
  return btn;
}

function choosePlayer(player) {
  pushRecentPlayer(player);
  selectPlayer(player.id);
}

cheaperOnlyCheckbox.addEventListener("change", () => currentPlayerId && loadSimilar(currentPlayerId));
anyPositionCheckbox.addEventListener("change", () => currentPlayerId && loadSimilar(currentPlayerId));

async function runSearch(query) {
  latestSearchQuery = query;
  const players = await api.listPlayers({ search: query });
  if (query !== latestSearchQuery) return; // a newer search superseded this one

  clear(resultsList);
  if (players.length === 0) {
    resultsList.hidden = true;
    return;
  }
  for (const player of players.slice(0, 10)) resultsList.appendChild(resultItem(player));
  resultsList.hidden = false;
}

async function selectPlayer(playerId) {
  currentPlayerId = playerId;
  resultsList.hidden = true;
  searchInput.value = "";
  emptyEl.hidden = true;
  detailEl.hidden = false;

  const player = await api.getPlayer(playerId);
  renderHeader(player);
  renderInjuryGauge(player);
  renderNextFixture(player);
  await Promise.all([loadTrend(playerId, player), loadSimilar(playerId)]);
}

function renderHeader(player) {
  clear(avatarEl);
  if (player.photo_url) {
    const img = document.createElement("img");
    img.src = player.photo_url;
    img.alt = player.full_name;
    img.addEventListener("error", () => {
      img.remove();
      avatarEl.textContent = initials(player.full_name);
    });
    avatarEl.appendChild(img);
  } else {
    avatarEl.textContent = initials(player.full_name);
  }

  nameEl.textContent = player.full_name;
  metaEl.textContent = `${player.team_short_name} · ${POSITION_NAMES[player.element_type]} · £${(player.now_cost / 10).toFixed(1)}m`;

  const existingTag = document.querySelector(".fq-nationality-tag");
  if (existingTag) existingTag.remove();
  if (player.nationality) {
    const tag = document.createElement("span");
    tag.className = "fq-nationality-tag";
    tag.textContent = player.nationality;
    metaEl.after(tag);
  }
}

function initials(fullName) {
  const parts = fullName.split(" ").filter(Boolean);
  const value = parts.length >= 2 ? parts[0][0] + parts[parts.length - 1][0] : (parts[0]?.[0] ?? "?");
  return value.toUpperCase();
}

function renderInjuryGauge(player) {
  clear(riskGaugeEl);
  if (!player.injury_risk) {
    gaugeWordEl.textContent = "Not available";
    gaugeBreakdownEl.textContent = "";
    return;
  }
  const pct = player.injury_risk.risk_pct;
  const color = pct < 15 ? "var(--fq-up)" : pct < 40 ? "var(--fq-warn)" : "var(--fq-down)";
  riskGaugeEl.appendChild(donutGauge(pct, color));
  gaugeWordEl.textContent = pct < 15 ? "Rarely misses a match" : pct < 40 ? "Worth keeping an eye on" : "Fragile lately";
  const age = player.injury_risk.age !== null ? player.injury_risk.age.toFixed(1) : "unknown";
  gaugeBreakdownEl.textContent = `Age ${age} · history ${player.injury_risk.history_component.toFixed(2)} · load ${player.injury_risk.load_component.toFixed(2)}`;
}

function renderNextFixture(player) {
  clear(fdrScaleEl);
  if (!player.next_opponent) {
    fixtureValueEl.textContent = "No fixture scheduled";
    fixtureNoteEl.textContent = "";
    return;
  }
  fixtureValueEl.textContent = `${player.next_opponent} (${player.next_opponent_is_home ? "H" : "A"})`;
  fixtureNoteEl.textContent = `FDR ${player.fixture_difficulty} · ${Math.round(player.chance_of_playing * 100)}% likely to play`;
  for (let fdr = 1; fdr <= 5; fdr++) {
    const bar = document.createElement("div");
    bar.className = "fq-fdr-bar";
    bar.style.background = FDR_COLORS[fdr];
    bar.style.opacity = fdr === player.fixture_difficulty ? "1" : "0.28";
    fdrScaleEl.appendChild(bar);
  }
}

async function loadTrend(playerId, player) {
  clear(trendChartEl);
  const history = await api.getPlayerHistory(playerId);
  if (history.length === 0) {
    trendSummaryEl.textContent = "";
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No gameweek history yet.";
    trendChartEl.appendChild(empty);
    return;
  }
  const points = history.map((h) => h.total_points);
  trendChartEl.appendChild(buildTrendChart(points));
  const avg = points.reduce((a, b) => a + b, 0) / points.length;
  trendSummaryEl.textContent = `${points.length} gameweeks · avg ${avg.toFixed(1)} pts/GW · form ${player.form.toFixed(1)}`;
}

const SVG_NS = "http://www.w3.org/2000/svg";

function buildTrendChart(values) {
  const width = 720;
  const height = 220;
  const top = 20;
  const bottom = 200;
  const left = 30;
  const right = 690;

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", height);
  svg.style.display = "block";
  svg.style.overflow = "visible";

  for (const y of [40, 100, 160, 200]) {
    const line = document.createElementNS(SVG_NS, "path");
    line.setAttribute("d", `M0 ${y} H${width}`);
    line.setAttribute("stroke", "var(--fq-line)");
    line.setAttribute("stroke-width", "1");
    svg.appendChild(line);
  }

  const max = Math.max(...values, 1);
  const step = values.length > 1 ? (right - left) / (values.length - 1) : 0;
  const coords = values.map((v, i) => [left + i * step, bottom - (v / max) * (bottom - top)]);

  const gradId = `fqgrad-${Math.random().toString(36).slice(2)}`;
  const defs = document.createElementNS(SVG_NS, "defs");
  const grad = document.createElementNS(SVG_NS, "linearGradient");
  grad.setAttribute("id", gradId);
  grad.setAttribute("x1", "0"); grad.setAttribute("y1", "0"); grad.setAttribute("x2", "0"); grad.setAttribute("y2", "1");
  const stop1 = document.createElementNS(SVG_NS, "stop");
  stop1.setAttribute("offset", "0%"); stop1.setAttribute("stop-color", "var(--fq-accent)"); stop1.setAttribute("stop-opacity", "0.34");
  const stop2 = document.createElementNS(SVG_NS, "stop");
  stop2.setAttribute("offset", "100%"); stop2.setAttribute("stop-color", "var(--fq-accent)"); stop2.setAttribute("stop-opacity", "0");
  grad.appendChild(stop1); grad.appendChild(stop2);
  defs.appendChild(grad);
  svg.appendChild(defs);

  const linePath = coords.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  const fillPath = `${linePath} L${coords[coords.length - 1][0]} ${bottom} L${coords[0][0]} ${bottom} Z`;

  const fill = document.createElementNS(SVG_NS, "path");
  fill.setAttribute("d", fillPath);
  fill.setAttribute("fill", `url(#${gradId})`);
  svg.appendChild(fill);

  const line = document.createElementNS(SVG_NS, "path");
  line.setAttribute("d", linePath);
  line.setAttribute("fill", "none");
  line.setAttribute("stroke", "var(--fq-accent)");
  line.setAttribute("stroke-width", "2.4");
  line.setAttribute("stroke-linecap", "round");
  line.setAttribute("stroke-linejoin", "round");
  svg.appendChild(line);

  coords.forEach(([cx, cy], i) => {
    const hitWidth = step || 40;
    const hitRect = document.createElementNS(SVG_NS, "rect");
    hitRect.setAttribute("x", cx - hitWidth / 2);
    hitRect.setAttribute("y", "0");
    hitRect.setAttribute("width", hitWidth);
    hitRect.setAttribute("height", bottom);
    hitRect.setAttribute("fill", "transparent");
    svg.appendChild(hitRect);

    const guide = document.createElementNS(SVG_NS, "line");
    guide.setAttribute("x1", cx); guide.setAttribute("x2", cx);
    guide.setAttribute("y1", "0"); guide.setAttribute("y2", bottom);
    guide.setAttribute("stroke", "var(--fq-accent)");
    guide.setAttribute("stroke-width", "1");
    guide.setAttribute("opacity", "0");
    svg.appendChild(guide);

    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("cx", cx); dot.setAttribute("cy", cy); dot.setAttribute("r", "3.4");
    dot.setAttribute("fill", "var(--fq-accent-hi)");
    dot.setAttribute("stroke", "var(--fq-surf)");
    dot.setAttribute("stroke-width", "2");
    svg.appendChild(dot);

    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", cx); label.setAttribute("y", bottom + 16);
    label.setAttribute("text-anchor", "middle"); label.setAttribute("font-size", "11");
    label.setAttribute("fill", "var(--fq-faint)");
    label.textContent = `GW${i + 1}`;
    svg.appendChild(label);

    const valueLabel = document.createElementNS(SVG_NS, "text");
    valueLabel.setAttribute("x", cx); valueLabel.setAttribute("y", cy - 14);
    valueLabel.setAttribute("text-anchor", "middle"); valueLabel.setAttribute("font-size", "12");
    valueLabel.setAttribute("font-weight", "500"); valueLabel.setAttribute("fill", "var(--fq-text)");
    valueLabel.setAttribute("opacity", "0");
    valueLabel.textContent = values[i];
    svg.appendChild(valueLabel);

    hitRect.addEventListener("mouseenter", () => {
      dot.setAttribute("r", "6");
      guide.setAttribute("opacity", "0.9");
      valueLabel.setAttribute("opacity", "1");
    });
    hitRect.addEventListener("mouseleave", () => {
      dot.setAttribute("r", "3.4");
      guide.setAttribute("opacity", "0");
      valueLabel.setAttribute("opacity", "0");
    });
  });

  return svg;
}

async function loadSimilar(playerId) {
  clear(similarGridEl);
  const results = await api.getSimilarPlayers(playerId, {
    cheaper_only: cheaperOnlyCheckbox.checked,
    any_position: anyPositionCheckbox.checked,
  });
  if (results.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No similar players found (needs gameweek history).";
    similarGridEl.appendChild(empty);
    return;
  }

  const maxSimilarity = Math.max(...results.map((r) => r.similarity), 0.0001);
  for (const r of results) {
    const card = document.createElement("div");
    card.className = "fq-similar-card";

    const head = document.createElement("div");
    head.className = "fq-similar-card__head";
    head.appendChild(jerseyIcon(kitFor(r.team_short_name), 22));
    const name = document.createElement("div");
    name.className = "fq-similar-card__name";
    name.textContent = r.web_name;
    head.appendChild(name);
    card.appendChild(head);

    const priceRow = document.createElement("div");
    priceRow.className = "fq-similar-card__row";
    const priceLabel = document.createElement("span");
    priceLabel.textContent = "Price";
    const priceValue = document.createElement("span");
    priceValue.textContent = `£${(r.now_cost / 10).toFixed(1)}m`;
    priceRow.appendChild(priceLabel);
    priceRow.appendChild(priceValue);
    card.appendChild(priceRow);

    const barHead = document.createElement("div");
    barHead.className = "fq-similar-card__bar-head";
    const barLabel = document.createElement("span");
    barLabel.textContent = "Similarity";
    const barValue = document.createElement("span");
    barValue.textContent = r.similarity.toFixed(2);
    barHead.appendChild(barLabel);
    barHead.appendChild(barValue);
    card.appendChild(barHead);

    const barTrack = document.createElement("div");
    barTrack.className = "fq-similar-card__bar-track";
    const barFill = document.createElement("div");
    barFill.className = "fq-similar-card__bar-fill";
    barFill.style.width = `${Math.round((r.similarity / maxSimilarity) * 100)}%`;
    barTrack.appendChild(barFill);
    card.appendChild(barTrack);

    similarGridEl.appendChild(card);
  }
}
