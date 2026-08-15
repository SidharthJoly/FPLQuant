#!/bin/bash
# Run via cron on the deployed VM — resolves/syncs Transfermarkt injury data.
# Weekly, not daily: this scrapes the full player pool at ~1.5s/request, see
# DEPLOYMENT.md and .github/workflows/ingest_injuries.yml for why.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T api uv run fplquant-ingest-injuries
