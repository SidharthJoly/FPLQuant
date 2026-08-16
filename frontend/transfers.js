import { api } from "./api.js";
import { statTile, clear, playerMetaLine } from "./components.js";

const POSITION_NAMES = { 1: "GKP", 2: "DEF", 3: "MID", 4: "FWD" };
const POSITION_ORDER = [1, 2, 3, 4];

const form = document.getElementById("transfers-form");
const riskCheckbox = document.getElementById("transfer-risk-adjusted");
const riskParams = document.getElementById("transfer-risk-params");
const statusEl = document.getElementById("transfers-status");
const resultsEl = document.getElementById("transfers-results");
const kpisEl = document.getElementById("transfers-kpis");
const verdictEl = document.getElementById("transfers-verdict");
const pairsEl = document.getElementById("transfers-pairs");
const currentSquadEl = document.getElementById("transfers-current-squad");
const squadEl = document.getElementById("transfers-squad");
const benchEl = document.getElementById("transfers-bench");

riskCheckbox.addEventListener("change", () => {
  riskParams.hidden = !riskCheckbox.checked;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Planning transfers…";
  statusEl.classList.remove("error");
  resultsEl.hidden = true;

  const payload = {
    fpl_team_id: Number(form.fpl_team_id.value),
    free_transfers: Number(form.free_transfers.value),
    chip: form.chip.value,
    max_per_club: Number(form.max_per_club.value),
    risk_adjusted: riskCheckbox.checked,
    risk_aversion: Number(form.risk_aversion.value),
    injury_weight: Number(form.injury_weight.value),
  };

  try {
    const result = await api.planTransfers(payload);
    renderResult(result);
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = `Could not plan transfers: ${err.message}`;
    statusEl.classList.add("error");
  }
});

function renderResult(result) {
  clear(kpisEl);
  clear(pairsEl);
  clear(currentSquadEl);
  clear(squadEl);
  clear(benchEl);

  kpisEl.appendChild(statTile({ label: "Team", value: result.team_name }));
  kpisEl.appendChild(statTile({ label: "Bank", value: `£${(result.bank / 10).toFixed(1)}m` }));
  kpisEl.appendChild(statTile({ label: "Free transfers", value: String(result.free_transfers) }));
  kpisEl.appendChild(
    statTile({
      label: "Hit cost",
      value: result.hit_cost > 0 ? `-${result.hit_cost} pts` : "None",
      delta: result.transfers_made > 0 ? `+${result.points_gain_after_hit.toFixed(1)} pts net` : null,
      deltaGood: result.points_gain_after_hit >= 0,
    })
  );

  renderVerdict(result);
  renderPairs(result.transfers);
  renderPlayerGroup(currentSquadEl, result.current_squad, null);
  renderPlayerGroup(squadEl, result.starting_xi.starters, result.starting_xi);
  renderPlayerGroup(benchEl, result.starting_xi.bench, result.starting_xi);

  resultsEl.hidden = false;
}

function renderVerdict(result) {
  clear(verdictEl);
  verdictEl.classList.remove("transfer-verdict--positive", "transfer-verdict--neutral");

  if (result.transfers_made === 0) {
    verdictEl.textContent = "No transfers recommended this week — your squad is already well positioned.";
    verdictEl.classList.add("transfer-verdict--neutral");
    return;
  }

  const chipNote =
    result.chip === "none"
      ? result.hit_cost > 0
        ? `costing ${result.hit_cost} points beyond your free transfers`
        : "within your free transfers, no points cost"
      : `using your ${result.chip === "wildcard" ? "Wildcard" : "Free Hit"}, no points cost`;

  verdictEl.textContent =
    `Recommended: ${result.transfers_made} transfer${result.transfers_made === 1 ? "" : "s"} ` +
    `${chipNote} — a net gain of +${result.points_gain_after_hit.toFixed(1)} points for the next match.`;
  verdictEl.classList.add("transfer-verdict--positive");
}

function renderPairs(transfers) {
  if (transfers.length === 0) return;
  for (const pair of transfers) {
    const row = document.createElement("div");
    row.className = "transfer-pair";

    row.appendChild(transferSide("OUT", "transfer-pair__out", pair.out));
    const arrow = document.createElement("span");
    arrow.className = "transfer-pair__arrow";
    arrow.textContent = "→";
    row.appendChild(arrow);
    row.appendChild(transferSide("IN", "transfer-pair__in", pair.player_in));

    pairsEl.appendChild(row);
  }
}

function transferSide(labelText, className, player) {
  const side = document.createElement("div");
  side.className = `transfer-pair__side ${className}`;

  const label = document.createElement("span");
  label.className = "transfer-pair__label";
  label.textContent = labelText;
  side.appendChild(label);

  side.appendChild(document.createTextNode(` ${player.web_name} (${player.team_short_name})`));
  return side;
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
      if (xi && player.player_id === xi.captain.player_id) {
        name.appendChild(badge("C"));
      } else if (xi && player.player_id === xi.vice_captain.player_id) {
        name.appendChild(badge("VC"));
      }

      const meta = document.createElement("span");
      meta.className = "squad-player__meta";
      meta.textContent = playerMetaLine(player);

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
