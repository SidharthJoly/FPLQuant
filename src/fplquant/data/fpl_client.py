from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from fplquant.config import settings


class FPLClient:
    """Thin wrapper around the public FPL API (fantasy.premierleague.com/api).

    No API key is required. Endpoints used:
      - /bootstrap-static/    teams, players, gameweeks (events)
      - /fixtures/            all fixtures for the season
      - /element-summary/{id}/  per-gameweek history for one player
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.fpl_base_url
        self.session = requests.Session()
        retries = Retry(
            total=settings.http_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _get(self, path: str) -> Any:
        response = self.session.get(f"{self.base_url}{path}", timeout=settings.http_timeout_seconds)
        response.raise_for_status()
        return response.json()

    def get_bootstrap_static(self) -> dict[str, Any]:
        return self._get("/bootstrap-static/")  # type: ignore[no-any-return]

    def get_fixtures(self) -> list[dict[str, Any]]:
        return self._get("/fixtures/")  # type: ignore[no-any-return]

    def get_element_summary(self, player_fpl_id: int) -> dict[str, Any]:
        return self._get(f"/element-summary/{player_fpl_id}/")  # type: ignore[no-any-return]

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "FPLClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
