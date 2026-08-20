# FPL Quant

[![CI](https://github.com/SidharthJoly/FPLQuant/actions/workflows/ci.yml/badge.svg)](https://github.com/SidharthJoly/FPLQuant/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/SidharthJoly/FPLQuant/main/badges/coverage.json)](https://github.com/SidharthJoly/FPLQuant/actions/workflows/ci.yml)

A Fantasy Premier League analytics and squad optimization platform. Treats players
like financial instruments — combining price momentum, volatility, and portfolio
theory with real sports analytics (injury risk, form) to select an optimal,
risk-adjusted squad.

## Status

✅ All 10 planned milestones are in place, and it's live:
**[fplquant.sidharthjoly.com](https://fplquant.sidharthjoly.com/)**
(frontend, GitHub Pages behind a custom subdomain) talking to a real backend
on an Oracle Cloud Always Free VM at `https://fplquant.duckdns.org` (see
[`DEPLOYMENT.md`](DEPLOYMENT.md)).

## Screenshots

Squad optimizer, player explorer, and the market view — the "Nocturne" quant-terminal
redesign, dark by default with a light-mode variant. Player positions in the
optimizer's starting-XI pitch view are jersey icons colored by each club's real kit.
**Demo data** — the 2026/27 season hasn't started yet, so these are
seeded with synthetic gameweek history on top of real FPL player/team data,
not live results.

<img src="docs/screenshots/optimizer.png" alt="Squad optimizer" width="720" />
<img src="docs/screenshots/explorer.png" alt="Player explorer" width="720" />
<img src="docs/screenshots/ticker.png" alt="Market view" width="720" />
<img src="docs/screenshots/ticker_dark.png" alt="Market view, light mode" width="720" />

## Architecture

FastAPI backend (SQLite + Redis cache) reused by both the CLIs and the API,
a fixture-adjusted expected-points model, an ILP-based squad optimizer and
transfer planner, and a vanilla-JS frontend ("Nocturne" — no build step). Full
write-up, including the fixture-adjustment model and transfer planner, in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Project layout

```
src/fplquant/
  config.py        typed settings (pydantic-settings), env-overridable
  models/           SQLAlchemy ORM models + engine/session setup
  data/             FPL API client + ingestion pipeline
  form/             EWMA-based form scoring (points + underlying stats)
  optimizer/        ILP squad selection (PuLP), budget/position/club constraints
  risk/             injury risk scoring + risk-adjusted expected points (Sharpe-style)
  market/           price/ownership momentum, points volatility, teammate correlation
  similarity/       per-90 stat vectors, cosine k-NN, PCA/t-SNE projection
  api/              FastAPI backend (routers/, schemas.py, cache.py — Redis)
frontend/           static dashboard (vanilla HTML/CSS/JS, served by the API)
alembic/            database migrations
tests/              pytest suite (mirrors src/ layout)
```

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
uv sync                       # install dependencies into .venv
cp .env.example .env          # optional — defaults work out of the box
uv run alembic upgrade head   # create data/fplquant.db and apply schema
uv run fplquant-ingest        # pull live data from the FPL API (~1-2 min)
uv run fplquant-form           # print the form leaderboard (once gameweeks exist)
uv run fplquant-optimize       # select an optimal 15-man squad within budget
```

Note: the form leaderboard is empty until gameweek data exists — the 2026/27
season's gameweek history only starts appearing in the FPL API once matches
have been played. The optimizer works either way: it falls back to FPL's own
`ep_next` estimate for players with no gameweek history yet, and switches to
our own EWMA-based points_form once it's available.

```bash
uv run fplquant-optimize --budget 100.0 --max-per-club 3

# Risk-adjusted: maximizes expected_points * (1 - injury_risk) / (1 + volatility
# penalty) instead of raw expected points — see src/fplquant/risk/adjusted.py
uv run fplquant-optimize --risk-adjusted --risk-aversion 1.0 --injury-weight 1.0
```

On top of the 15-man squad, both the CLI and `/optimize` also return a
starting XI: the best of FPL's 8 legal formations for that squad
(`src/fplquant/optimizer/starting_xi.py` — exhaustive search over the
formations, since points are additive per position there's no need for
another ILP), captain + vice-captain (top two starters by predicted
points), and the point value of using Bench Boost or Triple Captain that
week. Wildcard/Free Hit aren't covered — those are about *whether to
replace your current squad*, which needs a "my current team" concept this
app doesn't track.

Player similarity (per-90 stat vectors, cosine k-NN, PCA/t-SNE projection —
also needs real gameweek history, so it's empty preseason like the market layer):

```bash
uv run fplquant-similar "Haaland"                    # most similar players
uv run fplquant-similar "Haaland" --cheaper-only      # cheaper alternatives
uv run fplquant-projection --method pca --output player_projection.json
```

Injury risk (separate from the main ingest, since it scrapes Transfermarkt and
is rate-limited — see Data sources below):

```bash
uv run fplquant-ingest-injuries   # resolve player matches + sync injury history
uv run fplquant-risk              # print the injury risk leaderboard
uv run fplquant-market            # price/ownership momentum, volatility, correlation
```

Like the form leaderboard, `fplquant-market` is empty until gameweek data
exists — price momentum, points volatility, and teammate correlation are all
computed from the per-gameweek time series (`PlayerGameweekStat`), and there's
no meaningful preseason fallback for any of them (unlike the optimizer's
`ep_next` fallback). They populate automatically once gameweek 1 happens.

## API

```bash
uv run fplquant-api                    # serves at http://localhost:8000
# dashboard at / — Optimizer / Player Explorer / Market Ticker tabs
# interactive API docs at /docs (Swagger) and /redoc — auto-generated by FastAPI
```

Works with or without Redis running — caching is best-effort (falls through
to a fresh computation, logging a warning, if Redis is unreachable).

## Docker

```bash
docker compose up          # api (port 8000) + redis (port 6379), one command
docker compose exec api uv run fplquant-ingest   # populate data inside the container
```

The prebuilt image (`Dockerfile`) is published to
[GitHub Container Registry](https://github.com/sidharthjoly?tab=packages) on
every push to `main` and can be run directly, without cloning the repo:

```bash
docker run -p 8000:8000 \
  -e FPLQUANT_DATABASE_URL=sqlite:////app/data/fplquant.db \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/sidharthjoly/fplquant:latest
```

It needs a schema (`alembic upgrade head`) and data (`fplquant-ingest`)
before `/optimize` returns anything useful — `docker compose up` above wires
that in via `docker-compose.yml`'s startup command. See
[`src/fplquant/config.py`](src/fplquant/config.py) for the full list of
`FPLQUANT_*` environment variables (Redis URL, CORS origins, HTTP timeouts).
This same image runs in production on the deployed backend — built and
verified for real on the actual VM, not just locally; the VM pulls the
prebuilt image on deploy rather than rebuilding from source on its own
limited CPU (see [`DEPLOYMENT.md`](DEPLOYMENT.md)).

The frontend itself *was* visually verified — headless Chromium against a
locally-seeded database (real FPL bootstrap data plus synthetic gameweek
history, since the live 2026/27 season hasn't started), driving all three
tabs and both themes. That caught two real bugs before they shipped (a CSS
rule that kept the risk-adjusted inputs visible regardless of the checkbox,
and a number-formatting nit) — fixed and reverified.

## Development

```bash
uv run pytest                 # run tests (with coverage)
uv run ruff check .           # lint
uv run black .                # format
uv run mypy src               # type check
uv run pre-commit install     # enable pre-commit hooks (ruff, black, mypy)
```

Creating a new migration after changing `src/fplquant/models/orm.py`:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

## Data sources

FPL's own API (prices, points, fixtures, xG/xA/ICT) plus Transfermarkt
(injury history, scraped and fuzzy-matched to FPL players). Full breakdown,
including candidates investigated and not pursued, in
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Roadmap

1. ✅ Data pipeline (FPL API → SQLite via SQLAlchemy/Alembic)
2. ✅ Form analysis module (EWMA of points + underlying stats)
3. ✅ Basic ILP optimizer (budget/position/club constraints, maximize points)
4. ✅ Injury risk module (age, position, Transfermarkt injury history, minutes load)
5. ✅ "Stock market" layer (price momentum, volatility, correlation)
6. ✅ Risk-adjusted optimizer (Sharpe-style combined metric)
7. ✅ Player similarity finder (cosine similarity / k-NN, PCA/t-SNE viz)
8. ✅ FastAPI backend with Redis caching
9. ✅ Frontend dashboard (squad optimizer, player explorer, market ticker)
10. ✅ Fixture-adjusted predictions (opponent strength, venue, playing chance)
    and a transfer planner (FPL team ID pull, -4-hit-aware ILP recommendations,
    wildcard/free hit support)

## Deployment

Split across two hosts, both live:

- **Frontend** — [GitHub Pages](https://fplquant.sidharthjoly.com/), served
  behind a custom subdomain (`fplquant.sidharthjoly.com`, CNAMEd to
  `sidharthjoly.github.io`), deploys via `.github/workflows/pages.yml` on
  every push touching `frontend/`.
- **Backend** (FastAPI + Redis) — an Oracle Cloud "Always Free" VM
  (DigitalOcean's GitHub Student Pack offer expired before it got redeemed,
  so the plan moved here instead), fronted by Caddy at
  `https://fplquant.duckdns.org` for automatic, permanently-free HTTPS
  (DuckDNS + Let's Encrypt — no purchased domain, no expiring credit). Full
  runbook, including the OCI-specific firewall gotchas that came up setting
  this up, in [`DEPLOYMENT.md`](DEPLOYMENT.md). Redeploys via
  `.github/workflows/deploy.yml` (manually triggered).

The live server also keeps its own data fresh (cron on the VM,
`scripts/cron_ingest*.sh`) and stays clear of Oracle's idle-instance reclaim
policy (`.github/workflows/keepalive.yml`, pings `/health` every 15 min) —
both detailed in `DEPLOYMENT.md`.

## License

TBD.
