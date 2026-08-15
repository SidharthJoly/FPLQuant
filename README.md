# FPL Quant

A Fantasy Premier League analytics and squad optimization platform. Treats players
like financial instruments — combining price momentum, volatility, and portfolio
theory with real sports analytics (injury risk, form) to select an optimal,
risk-adjusted squad.

## Status

🚧 Early scaffold. Milestone 1 (data pipeline) is in place; everything else in the
roadmap below is still to come.

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
```

A scheduled GitHub Actions workflow (`.github/workflows/ingest.yml`) runs the
ingest daily and uploads the resulting SQLite database as a build artifact.

## Project layout

```
src/fplquant/
  config.py        typed settings (pydantic-settings), env-overridable
  models/           SQLAlchemy ORM models + engine/session setup
  data/             FPL API client + ingestion pipeline
  optimizer/        (planned) ILP squad optimizer
  risk/             (planned) injury risk + volatility scoring
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
  history, fixtures, and FPL's own xG/xA/ICT stats. No API key required.
  This is the only source wired up so far.
- **FBref / StatsBomb open data** — richer underlying stats (progressive
  passes, etc). Planned.
- **Transfermarkt** — age and injury history, for the injury risk module.
  Planned.

## Roadmap

1. ✅ Data pipeline (FPL API → SQLite via SQLAlchemy/Alembic)
2. ⬜ Form analysis module (EWMA of points + underlying stats)
3. ⬜ Basic ILP optimizer (budget/position/club constraints, maximize points)
4. ⬜ Injury risk module
5. ⬜ "Stock market" layer (price momentum, volatility, correlation)
6. ⬜ Risk-adjusted optimizer (Sharpe-style combined metric)
7. ⬜ Player similarity finder (cosine similarity / k-NN, PCA/t-SNE viz)
8. ⬜ FastAPI backend with Redis caching
9. ⬜ Frontend dashboard

## License

TBD.
