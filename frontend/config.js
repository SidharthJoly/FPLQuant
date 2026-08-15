// API base URL. Empty string = same-origin (the default when the FastAPI
// backend serves this dashboard itself, e.g. local dev or `fplquant-api`).
//
// When this dashboard is deployed separately (e.g. GitHub Pages), the API
// runs on a different origin — set API_BASE to that origin here before
// deploying. Example:
//   export const API_BASE = "https://api.fplquant.example.com";
export const API_BASE = "";
