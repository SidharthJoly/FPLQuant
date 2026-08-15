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

let currentPlayerId = null;
let searchDebounce = null;
let latestSearchQuery = "";

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  const query = searchInput.value.trim();
  if (query.length < 2) {
    latestSearchQuery = "";
    resultsList.hidden = true;
    return;
  }
  searchDebounce = setTimeout(() => runSearch(query), 250);
});

document.addEventListener("click", (event) => {
  if (!resultsList.contains(event.target) && event.target !== searchInput) {
    resultsList.hidden = true;
  }
});

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
    const li = document.createElement("li");
    li.textContent = `${player.web_name} (${player.team_short_name}, ${POSITION_NAMES[player.element_type]})`;
    li.addEventListener("click", () => selectPlayer(player.id));
    resultsList.appendChild(li);
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
  const left = document.createElement("div");
  const h2 = document.createElement("h2");
  h2.textContent = player.web_name;
  const meta = document.createElement("div");
  meta.className = "player-header__meta";
  meta.textContent = `${player.team_short_name} · ${POSITION_NAMES[player.element_type]} · £${(player.now_cost / 10).toFixed(1)}m`;
  left.appendChild(h2);
  left.appendChild(meta);
  playerHeaderEl.appendChild(left);
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
