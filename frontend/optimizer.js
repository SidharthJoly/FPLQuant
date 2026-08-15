import { api } from "./api.js";
import { statTile, clear } from "./components.js";

const POSITION_NAMES = { 1: "GKP", 2: "DEF", 3: "MID", 4: "FWD" };
const POSITION_ORDER = [1, 2, 3, 4];

const form = document.getElementById("optimizer-form");
const riskCheckbox = document.getElementById("risk-adjusted");
const riskParams = document.getElementById("risk-params");
const statusEl = document.getElementById("optimizer-status");
const resultsEl = document.getElementById("optimizer-results");
const kpisEl = document.getElementById("optimizer-kpis");
const squadEl = document.getElementById("optimizer-squad");

riskCheckbox.addEventListener("change", () => {
  riskParams.hidden = !riskCheckbox.checked;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Building squad…";
  statusEl.classList.remove("error");
  resultsEl.hidden = true;

  const payload = {
    budget: Number(form.budget.value),
    max_per_club: Number(form.max_per_club.value),
    risk_adjusted: riskCheckbox.checked,
    risk_aversion: Number(form.risk_aversion.value),
    injury_weight: Number(form.injury_weight.value),
  };

  try {
    const result = await api.optimize(payload);
    renderResult(result, payload.risk_adjusted);
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = `Could not build a squad: ${err.message}`;
    statusEl.classList.add("error");
  }
});

function renderResult(result, riskAdjusted) {
  clear(kpisEl);
  clear(squadEl);

  const pointsLabel = riskAdjusted ? "Risk-adjusted points" : "Predicted points";
  kpisEl.appendChild(
    statTile({ label: "Total cost", value: `£${(result.total_cost / 10).toFixed(1)}m` })
  );
  kpisEl.appendChild(
    statTile({ label: pointsLabel, value: result.total_predicted_points.toFixed(1) })
  );
  kpisEl.appendChild(statTile({ label: "Squad size", value: `${result.squad.length}` }));

  const byPosition = {};
  for (const player of result.squad) {
    (byPosition[player.element_type] ??= []).push(player);
  }

  for (const position of POSITION_ORDER) {
    const players = byPosition[position];
    if (!players) continue;
    players.sort((a, b) => b.predicted_points - a.predicted_points);

    const card = document.createElement("div");
    card.className = "squad-position";

    const heading = document.createElement("h4");
    heading.textContent = POSITION_NAMES[position];
    card.appendChild(heading);

    for (const player of players) {
      const row = document.createElement("div");
      row.className = "squad-player";

      const name = document.createElement("span");
      name.className = "squad-player__name";
      name.textContent = `${player.web_name} (${player.team_short_name})`;

      const meta = document.createElement("span");
      meta.className = "squad-player__meta";
      meta.textContent = `£${(player.now_cost / 10).toFixed(1)}m · ${player.predicted_points.toFixed(2)} pts`;

      row.appendChild(name);
      row.appendChild(meta);
      card.appendChild(row);
    }

    squadEl.appendChild(card);
  }

  resultsEl.hidden = false;
}
