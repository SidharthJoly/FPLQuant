# Data sources

- **FPL API** (`fantasy.premierleague.com/api`) — prices, ownership %, points
  history, fixtures, birth dates, and FPL's own xG/xA/ICT/ep_next stats. No
  API key required.
- **Transfermarkt** (`transfermarkt.com`) — injury history (type, dates, days
  out, games missed). No official API — scraped via `TransfermarktClient`
  (`src/fplquant/data/transfermarkt_client.py`), identifying as a standard
  browser and rate-limited (~1.5s/request, configurable via
  `FPLQUANT_TRANSFERMARKT_REQUEST_DELAY_SECONDS`) to stay polite to their
  servers. Players are matched by fuzzy name + club similarity
  (`player_matching.py`); ambiguous/unmatched players are skipped rather than
  guessed at. Intended for personal, non-commercial analytics use — this is
  markup-scraping, not an API contract, so it may need adjustment if
  Transfermarkt changes their page structure.
- **FBref / StatsBomb open data** — investigated, not pursued. StatsBomb's
  open dataset (github.com/statsbomb/open-data) doesn't cover any recent
  Premier League season (last EPL coverage: 2015/16), so it can't enrich the
  current player pool. FBref has the right current-season data
  (progressive passes, etc.) but sits behind a Cloudflare bot challenge that
  blocks even a real headless browser — a deliberate anti-scraping measure,
  not light filtering, so it wasn't pursued further. A second candidate
  (one-versus-one.com) was technically scrapable but explicitly disallows
  `ClaudeBot` and most AI crawlers by name in `robots.txt`, so that wasn't
  pursued either. FPL's own `ict_index`/`creativity`/`threat`/`influence`
  and xG/xA remain the underlying-stats signal used throughout (form
  scoring, injury risk, similarity finder).
