import { api } from "./api.js";
import { sparkline, clear } from "./components.js";

const TOP_N = 15;

const lookbackInput = document.getElementById("ticker-lookback");
const refreshBtn = document.getElementById("ticker-refresh");
const stripEl = document.getElementById("ticker-strip");
const emptyEl = document.getElementById("ticker-empty");

refreshBtn.addEventListener("click", loadTicker);

export async function loadTicker() {
  clear(stripEl);
  emptyEl.hidden = true;

  const lookback = Number(lookbackInput.value) || 5;
  const momentum = await api.getMarketMomentum({ top: TOP_N, lookback });

  if (momentum.length === 0) {
    emptyEl.hidden = false;
    return;
  }

  const histories = await Promise.all(
    momentum.map((m) => api.getPlayerHistory(m.player_id).catch(() => []))
  );

  momentum.forEach((m, i) => {
    stripEl.appendChild(buildCard(m, histories[i]));
  });
}

function buildCard(momentum, history) {
  const card = document.createElement("div");
  card.className = "ticker-card";

  const name = document.createElement("div");
  name.className = "ticker-card__name";
  name.textContent = momentum.web_name;
  card.appendChild(name);

  const points = history.map((h) => h.total_points);
  if (points.length > 0) {
    card.appendChild(sparkline(points, { width: 168, height: 36 }));
  }

  const priceRow = document.createElement("div");
  priceRow.className = "ticker-card__row";
  const priceGood = momentum.price_change >= 0;
  priceRow.innerHTML = "";
  const priceLabel = document.createElement("span");
  priceLabel.textContent = "Price";
  const priceValue = document.createElement("span");
  priceValue.className = priceGood ? "good" : "bad";
  priceValue.textContent = `${priceGood ? "▲" : "▼"} £${(momentum.price_change / 10).toFixed(1)}m`;
  priceRow.appendChild(priceLabel);
  priceRow.appendChild(priceValue);
  card.appendChild(priceRow);

  const ownershipRow = document.createElement("div");
  ownershipRow.className = "ticker-card__row";
  const ownershipGood = momentum.ownership_change >= 0;
  const ownershipLabel = document.createElement("span");
  ownershipLabel.textContent = "Ownership";
  const ownershipValue = document.createElement("span");
  ownershipValue.className = ownershipGood ? "good" : "bad";
  ownershipValue.textContent = `${ownershipGood ? "▲" : "▼"} ${(momentum.ownership_change_pct * 100).toFixed(1)}%`;
  ownershipRow.appendChild(ownershipLabel);
  ownershipRow.appendChild(ownershipValue);
  card.appendChild(ownershipRow);

  return card;
}
