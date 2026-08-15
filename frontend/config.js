// API base URL. Empty string = same-origin (the default when the FastAPI
// backend serves this dashboard itself, e.g. local dev or `fplquant-api`).
//
// When this dashboard is deployed separately (e.g. GitHub Pages), the API
// runs on a different origin — set API_BASE to that origin here before
// deploying. Example:
//   export const API_BASE = "https://api.fplquant.example.com";
//
// TODO: switch to https://<custom-domain> once the Student Pack domain +
// Caddy/a named Cloudflare tunnel are set up (DEPLOYMENT.md §4). The
// trycloudflare.com URL below is a *quick* tunnel — it changes on every
// `cloudflared` restart, so this line will need updating again if the
// tunnel process ever restarts before a permanent domain is in place.
export const API_BASE = "https://clouds-trackback-pension-exemption.trycloudflare.com";
