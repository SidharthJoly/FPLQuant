from typing import Any

from fastapi.testclient import TestClient

import fplquant.api.routers.meta as meta_router


class StubFPLClient:
    def __init__(self, bootstrap: dict[str, Any]) -> None:
        self._bootstrap = bootstrap

    def get_bootstrap_static(self) -> dict[str, Any]:
        return self._bootstrap

    def close(self) -> None:
        pass

    def __enter__(self) -> "StubFPLClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()


def test_next_deadline_picks_the_earliest_unfinished_event(
    api_client: TestClient, monkeypatch: Any
) -> None:
    stub = StubFPLClient(
        bootstrap={
            "events": [
                {"id": 1, "finished": True, "deadline_time": "2026-08-14T17:30:00Z"},
                {"id": 3, "finished": False, "deadline_time": "2026-09-04T17:30:00Z"},
                {"id": 2, "finished": False, "deadline_time": "2026-08-28T17:30:00Z"},
            ]
        }
    )
    monkeypatch.setattr(meta_router, "FPLClient", lambda: stub)

    response = api_client.get("/meta/next-deadline")

    assert response.status_code == 200
    body = response.json()
    assert body["gameweek"] == 2
    assert body["deadline"] == "2026-08-28T17:30:00Z"


def test_next_deadline_returns_null_when_season_is_over(
    api_client: TestClient, monkeypatch: Any
) -> None:
    stub = StubFPLClient(
        bootstrap={"events": [{"id": 1, "finished": True, "deadline_time": "2026-08-14T17:30:00Z"}]}
    )
    monkeypatch.setattr(meta_router, "FPLClient", lambda: stub)

    response = api_client.get("/meta/next-deadline")

    assert response.status_code == 200
    assert response.json() == {"deadline": None, "gameweek": None}
