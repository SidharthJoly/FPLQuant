#!/bin/bash
# Run via cron on the deployed VM to keep the live server's FPL data fresh.
# See DEPLOYMENT.md for the crontab entry. -T disables pseudo-TTY allocation,
# required for docker compose exec to work correctly from a non-interactive
# cron context.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T api uv run fplquant-ingest
