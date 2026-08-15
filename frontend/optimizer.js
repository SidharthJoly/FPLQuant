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
const chipsEl = document.getElementById("optimizer-chips");
const squadEl = document.getElementById("optimizer-squad");
const benchEl = document.getElementById("optimizer-bench");

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
  clear(chipsEl);
  clear(squadEl);
  clear(benchEl);

  const xi = result.starting_xi;
  const pointsLabel = riskAdjusted ? "risk-adjusted points" : "predicted points";

  kpisEl.appendChild(
    statTile({ label: "Total cost", value: `£${(result.total_cost / 10).toFixed(1)}m` })
  );
  kpisEl.appendChild(
    statTile({
      label: `Starting XI ${pointsLabel}`,
      value: xi.starting_predicted_points.toFixed(1),
    })
  );
  kpisEl.appendChild(statTile({ label: "Formation", value: xi.formation }));
  kpisEl.appendChild(statTile({ label: "Captain", value: xi.captain.web_name }));

  chipsEl.textContent =
    `Bench Boost would add +${xi.bench_boost_value.toFixed(1)} pts this week · ` +
    `Triple Captain would add +${xi.triple_captain_value.toFixed(1)} pts (over normal captaincy)`;

  renderPlayerGroup(squadEl, xi.starters, xi);
  renderPlayerGroup(benchEl, xi.bench, xi);

  resultsEl.hidden = false;
}

function renderPlayerGroup(container, players, xi) {
  const byPosition = {};
  for (const player of players) {
    (byPosition[player.element_type] ??= []).push(player);
  }

  for (const position of POSITION_ORDER) {
    const positionPlayers = byPosition[position];
    if (!positionPlayers) continue;
    positionPlayers.sort((a, b) => b.predicted_points - a.predicted_points);

    const card = document.createElement("div");
    card.className = "squad-position";

    const heading = document.createElement("h4");
    heading.textContent = POSITION_NAMES[position];
    card.appendChild(heading);

    for (const player of positionPlayers) {
      const row = document.createElement("div");
      row.className = "squad-player";

      const name = document.createElement("span");
      name.className = "squad-player__name";
      name.textContent = `${player.web_name} (${player.team_short_name})`;
      if (player.player_id === xi.captain.player_id) {
        name.appendChild(badge("C"));
      } else if (player.player_id === xi.vice_captain.player_id) {
        name.appendChild(badge("VC"));
      }

      const meta = document.createElement("span");
      meta.className = "squad-player__meta";
      meta.textContent = `£${(player.now_cost / 10).toFixed(1)}m · ${player.predicted_points.toFixed(2)} pts`;

      row.appendChild(name);
      row.appendChild(meta);
      card.appendChild(row);
    }

    container.appendChild(card);
  }
}

function badge(text) {
  const el = document.createElement("span");
  el.className = "captain-badge";
  el.textContent = text;
  return el;
}
