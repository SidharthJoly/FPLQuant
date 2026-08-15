// API base URL. Empty string = same-origin (the default when the FastAPI
// backend serves this dashboard itself, e.g. local dev or `fplquant-api`).
//
// When this dashboard is deployed separately (e.g. GitHub Pages), the API
// runs on a different origin — set API_BASE to that origin here before
// deploying. Example:
//   export const API_BASE = "https://api.fplquant.example.com";
//
// Permanent: fplquant.duckdns.org (free DuckDNS subdomain) -> Caddy on the
// Oracle Cloud VM -> the API on localhost:8000. Caddy auto-manages a real
// Let's Encrypt certificate for this hostname, no expiring quick-tunnel URL
// involved. If the VM's IP ever changes (e.g. instance recreated), update
// the DuckDNS record's IP — this URL itself doesn't need to change.
export const API_BASE = "https://fplquant.duckdns.org";
