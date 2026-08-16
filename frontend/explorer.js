import { api } from "./api.js";
import { sparkline, riskBadge, dataTable, emptyState, clear } from "./components.js";

const POSITION_NAMES = { 1: "GKP", 2: "DEF", 3: "MID", 4: "FWD" };

const searchInput = document.getElementById("player-search");
const resultsList = document.getElementById("search-results");
const emptyEl = document.getElementById("explorer-empty");
const detailEl = document.getElementById("explorer-detail");
const playerHeaderEl = document.getElementById("player-header");
const formTrendEl = document.getElementById("form-trend");
const injuryRiskEl = document.getElementById("injury-risk");
const similarPlayersEl = document.getElementById("similar-players");
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
  if (query.length === 0) {
    showSuggestions();
  } else if (query.length >= 2) {
    runSearch(query);
  }
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
  const header = document.createElement("li");
  header.className = "search-results__header";
  header.textContent = label;
  resultsList.appendChild(header);
  for (const player of players) {
    resultsList.appendChild(resultItem(player));
  }
}

function resultItem(player) {
  const li = document.createElement("li");
  li.textContent = `${player.web_name} (${player.team_short_name}, ${POSITION_NAMES[player.element_type]})`;
  li.addEventListener("click", () => choosePlayer(player));
  return li;
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
  if (query !== latestSearchQuery) {
    return; // a newer search superseded this one — discard the stale response
  }

  clear(resultsList);
  if (players.length === 0) {
    resultsList.hidden = true;
    return;
  }
  for (const player of players.slice(0, 10)) {
    resultsList.appendChild(resultItem(player));
  }
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
  await Promise.all([loadFormTrend(playerId, player), loadInjuryRisk(player), loadSimilar(playerId)]);
}

function renderHeader(player) {
  clear(playerHeaderEl);

  const avatar = document.createElement("div");
  avatar.className = "player-header__avatar";
  if (player.photo_url) {
    const img = document.createElement("img");
    img.className = "player-header__photo";
    img.src = player.photo_url;
    img.alt = player.full_name;
    img.addEventListener("error", () => {
      img.remove();
      avatar.appendChild(initialsAvatar(player));
    });
    avatar.appendChild(img);
  } else {
    avatar.appendChild(initialsAvatar(player));
  }

  const info = document.createElement("div");
  const h2 = document.createElement("h2");
  h2.textContent = player.full_name;
  const meta = document.createElement("div");
  meta.className = "player-header__meta";
  meta.textContent = `${player.team_short_name} · ${POSITION_NAMES[player.element_type]} · £${(player.now_cost / 10).toFixed(1)}m`;
  info.appendChild(h2);
  info.appendChild(meta);
  if (player.nationality) {
    const badge = document.createElement("span");
    badge.className = "nationality-badge";
    badge.textContent = player.nationality;
    info.appendChild(badge);
  }

  playerHeaderEl.appendChild(avatar);
  playerHeaderEl.appendChild(info);
}

function initialsAvatar(player) {
  const el = document.createElement("div");
  el.className = "player-header__initials";
  const parts = player.full_name.split(" ").filter(Boolean);
  const initials = parts.length >= 2 ? parts[0][0] + parts[parts.length - 1][0] : (parts[0]?.[0] ?? "?");
  el.textContent = initials.toUpperCase();
  return el;
}

async function loadFormTrend(playerId, player) {
  clear(formTrendEl);
  const history = await api.getPlayerHistory(playerId);
  if (history.length === 0) {
    formTrendEl.appendChild(emptyState("No gameweek history yet."));
    return;
  }
  const points = history.map((h) => h.total_points);
  formTrendEl.appendChild(sparkline(points));

  const summary = document.createElement("div");
  summary.className = "stat-tile__delta";
  const avg = points.reduce((a, b) => a + b, 0) / points.length;
  summary.textContent = `${points.length} gameweeks · avg ${avg.toFixed(1)} pts/GW · form ${player.form.toFixed(1)}`;
  formTrendEl.appendChild(summary);
}

function loadInjuryRisk(player) {
  clear(injuryRiskEl);
  if (!player.injury_risk) {
    injuryRiskEl.appendChild(emptyState("Injury risk not available."));
    return;
  }
  const badge = riskBadge(player.injury_risk.risk_pct);
  injuryRiskEl.appendChild(badge);

  const breakdown = document.createElement("div");
  breakdown.className = "stat-tile__delta";
  const age = player.injury_risk.age !== null ? player.injury_risk.age.toFixed(1) : "unknown";
  breakdown.textContent = `Age ${age} · history ${player.injury_risk.history_component.toFixed(2)} · load ${player.injury_risk.load_component.toFixed(2)}`;
  injuryRiskEl.appendChild(breakdown);
}

async function loadSimilar(playerId) {
  clear(similarPlayersEl);
  const results = await api.getSimilarPlayers(playerId, {
    cheaper_only: cheaperOnlyCheckbox.checked,
    any_position: anyPositionCheckbox.checked,
  });
  if (results.length === 0) {
    similarPlayersEl.appendChild(emptyState("No similar players found (needs gameweek history)."));
    return;
  }
  const table = dataTable(
    [
      { label: "Player", key: "web_name" },
      { label: "Cost", render: (r) => `£${(r.now_cost / 10).toFixed(1)}m` },
      { label: "Similarity", render: (r) => r.similarity.toFixed(2) },
    ],
    results
  );
  similarPlayersEl.appendChild(table);
}
