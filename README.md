# FPL Quant

A Fantasy Premier League analytics and squad optimization platform. Treats players
like financial instruments — combining price momentum, volatility, and portfolio
theory with real sports analytics (injury risk, form) to select an optimal,
risk-adjusted squad.

## Status

🚧 Early scaffold. Milestones 1–4 (data pipeline, form analysis, basic ILP
optimizer, injury risk) are in place; everything else in the roadmap below is
still to come.

## Architecture (current)

```
FPL API (fantasy.premierleague.com/api)
        │
        ▼
FPLClient (src/fplquant/data/fpl_client.py)   — HTTP wrapper, retries
        │
        ▼
ingest.py (src/fplquant/data/ingest.py)       — upserts into ORM models
        │
        ▼
SQLAlchemy ORM (src/fplquant/models/orm.py)   — Team, Player, Fixture,
        │                                        PlayerGameweekStat
        ▼
SQLite (data/fplquant.db), schema managed by Alembic (alembic/)

Transfermarkt (transfermarkt.com)
        │
        ▼
TransfermarktClient (src/fplquant/data/transfermarkt_client.py) — scrapes
        │                                     player search + injury history
        ▼
player_matching.py                    — fuzzy name+club matching to FPL players
        │
        ▼
ingest_injuries.py                    — caches the match, syncs InjuryRecord rows
```

Two scheduled GitHub Actions workflows keep the database fresh:
- `.github/workflows/ingest.yml` — daily, pulls prices/points/fixtures from the FPL API
- `.github/workflows/ingest_injuries.yml` — weekly, resolves + syncs Transfermarkt
  injury history (lower frequency since it's rate-limited scraping over the full
  player pool)

Both upload the resulting SQLite database as a build artifact.

## Project layout

```
src/fplquant/
  config.py        typed settings (pydantic-settings), env-overridable
  models/           SQLAlchemy ORM models + engine/session setup
  data/             FPL API client + ingestion pipeline
  form/             EWMA-based form scoring (points + underlying stats)
  optimizer/        ILP squad selection (PuLP), budget/position/club constraints
  risk/             injury risk scoring (age, position, history, minutes load)
  similarity/        (planned) player similarity / cheaper-alternative finder
  api/              (planned) FastAPI backend
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
```

Injury risk (separate from the main ingest, since it scrapes Transfermarkt and
is rate-limited — see Data sources below):

```bash
uv run fplquant-ingest-injuries   # resolve player matches + sync injury history
uv run fplquant-risk              # print the injury risk leaderboard
```

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
- **FBref / StatsBomb open data** — richer underlying stats (progressive
  passes, etc). Planned.

## Roadmap

1. ✅ Data pipeline (FPL API → SQLite via SQLAlchemy/Alembic)
2. ✅ Form analysis module (EWMA of points + underlying stats)
3. ✅ Basic ILP optimizer (budget/position/club constraints, maximize points)
4. ✅ Injury risk module (age, position, Transfermarkt injury history, minutes load)
5. ⬜ "Stock market" layer (price momentum, volatility, correlation)
6. ⬜ Risk-adjusted optimizer (Sharpe-style combined metric)
7. ⬜ Player similarity finder (cosine similarity / k-NN, PCA/t-SNE viz)
8. ⬜ FastAPI backend with Redis caching
9. ⬜ Frontend dashboard

## License

TBD.
