const SVG_NS = "http://www.w3.org/2000/svg";

export function statTile({ label, value, delta = null, deltaGood = true }) {
  const el = document.createElement("div");
  el.className = "stat-tile";

  const labelEl = document.createElement("div");
  labelEl.className = "stat-tile__label";
  labelEl.textContent = label;
  el.appendChild(labelEl);

  const valueEl = document.createElement("div");
  valueEl.className = "stat-tile__value";
  valueEl.textContent = value;
  el.appendChild(valueEl);

  if (delta !== null && delta !== undefined) {
    const deltaEl = document.createElement("div");
    deltaEl.className = `stat-tile__delta ${deltaGood ? "good" : "bad"}`;
    deltaEl.textContent = delta;
    el.appendChild(deltaEl);
  }

  return el;
}

/** A 12-point-style mini trend line: filled wash under a 2px line, end dot. */
export function sparkline(values, { width = 240, height = 48 } = {}) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "sparkline");
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  if (!values || values.length === 0) {
    return svg;
  }
  if (values.length === 1) {
    values = [values[0], values[0]];
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = 4;
  const step = (width - pad * 2) / (values.length - 1);

  const points = values.map((v, i) => {
    const x = pad + i * step;
    const y = height - pad - ((v - min) / range) * (height - pad * 2);
    return [x, y];
  });

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ");
  const fillPath = `${linePath} L${points[points.length - 1][0]},${height} L${points[0][0]},${height} Z`;

  const fill = document.createElementNS(SVG_NS, "path");
  fill.setAttribute("class", "fill");
  fill.setAttribute("d", fillPath);
  svg.appendChild(fill);

  const line = document.createElementNS(SVG_NS, "path");
  line.setAttribute("class", "line");
  line.setAttribute("d", linePath);
  svg.appendChild(line);

  const [lastX, lastY] = points[points.length - 1];
  const dot = document.createElementNS(SVG_NS, "circle");
  dot.setAttribute("cx", lastX);
  dot.setAttribute("cy", lastY);
  dot.setAttribute("r", 4);
  svg.appendChild(dot);

  return svg;
}

export function riskBadge(riskPct) {
  const el = document.createElement("span");
  const level = riskPct < 15 ? "low" : riskPct < 40 ? "medium" : "high";
  el.className = `risk-badge ${level}`;
  el.textContent = `${riskPct.toFixed(1)}%`;
  return el;
}

export function dataTable(columns, rows) {
  const table = document.createElement("table");
  table.className = "data-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const col of columns) {
    const th = document.createElement("th");
    th.textContent = col.label;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const col of columns) {
      const td = document.createElement("td");
      const value = col.render ? col.render(row) : row[col.key];
      if (value instanceof Node) {
        td.appendChild(value);
      } else {
        td.textContent = value;
      }
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  return table;
}

export function emptyState(message) {
  const el = document.createElement("div");
  el.className = "empty-state";
  const p = document.createElement("p");
  p.textContent = message;
  el.appendChild(p);
  return el;
}

export function clear(el) {
  el.replaceChildren();
}

/** Cost/points plus, when available, next opponent/venue/difficulty and
 * playing-chance — the "will they have a good game against this opponent at
 * this venue" context behind why a player was picked, benched, or offered
 * as a transfer target. */
export function playerMetaLine(player) {
  let text = `£${(player.now_cost / 10).toFixed(1)}m · ${player.predicted_points.toFixed(2)} pts`;
  if (player.next_opponent) {
    const venue = player.next_opponent_is_home ? "H" : "A";
    text += ` · vs ${player.next_opponent} (${venue})`;
    if (player.fixture_difficulty) {
      text += ` · FDR ${player.fixture_difficulty}`;
    }
  }
  if (player.chance_of_playing < 1) {
    text += ` · ${Math.round(player.chance_of_playing * 100)}% to play`;
  }
  return text;
}
