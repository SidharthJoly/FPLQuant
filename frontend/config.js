// API base URL, auto-detected so this file never needs hand-editing when
// switching between local dev and the deployed site (and so testing
// against a local server never silently hits production instead):
//
// - localhost / 127.0.0.1 (e.g. `fplquant-api`, `uv run uvicorn ...`,
//   `docker compose up`)     -> same-origin ("")
// - anywhere else (GitHub Pages, or this file opened directly)
//   -> the deployed backend: fplquant.duckdns.org (free DuckDNS subdomain)
//   -> Caddy on the Oracle Cloud VM -> the API on localhost:8000. Caddy
//   auto-manages a real Let's Encrypt certificate for this hostname. If the
//   VM's IP ever changes (e.g. instance recreated), update the DuckDNS
//   record's IP — this URL itself doesn't need to change.
const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
export const API_BASE = isLocal ? "" : "https://fplquant.duckdns.org";
