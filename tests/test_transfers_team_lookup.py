from typing import Any

import pytest
import requests
from sqlalchemy.orm import Session

from fplquant.models.orm import Player, Team
from fplquant.transfers.team_lookup import (
    TeamNotFoundError,
    fetch_current_squad,
    latest_locked_event,
)

PAST_EVENT = {"id": 1, "deadline_time": "2020-01-01T00:00:00Z"}
FUTURE_EVENT = {"id": 2, "deadline_time": "2099-01-01T00:00:00Z"}


class StubFPLClient:
    def __init__(
        self,
        bootstrap: dict[str, Any],
        entry: dict[str, Any] | None = None,
        picks: dict[str, Any] | None = None,
        picks_error: Exception | None = None,
    ) -> None:
        self._bootstrap = bootstrap
        self._entry = entry
        self._picks = picks
        self._picks_error = picks_error

    def get_bootstrap_static(self) -> dict[str, Any]:
        return self._bootstrap

    def get_entry(self, team_id: int) -> dict[str, Any]:
        assert self._entry is not None
        return self._entry

    def get_entry_picks(self, team_id: int, event_id: int) -> dict[str, Any]:
        if self._picks_error is not None:
            raise self._picks_error
        assert self._picks is not None
        return self._picks


def _team(session: Session, fpl_id: int = 1, short_name: str = "ARS") -> Team:
    team = Team(fpl_id=fpl_id, name=short_name, short_name=short_name)
    session.add(team)
    session.flush()
    return team


def _player(session: Session, team: Team, fpl_id: int, web_name: str) -> Player:
    player = Player(
        fpl_id=fpl_id,
        team_id=team.id,
        first_name=web_name,
        second_name=web_name,
        web_name=web_name,
        element_type=3,
        now_cost=50,
        status="a",
    )
    session.add(player)
    session.flush()
    return player


def test_latest_locked_event_picks_the_highest_passed_deadline() -> None:
    assert latest_locked_event([PAST_EVENT, FUTURE_EVENT]) == 1


def test_latest_locked_event_returns_none_before_any_deadline_passes() -> None:
    assert latest_locked_event([FUTURE_EVENT]) is None


def test_latest_locked_event_returns_none_for_no_events() -> None:
    assert latest_locked_event([]) is None


def test_fetch_current_squad_raises_before_season_starts(db_session: Session) -> None:
    client = StubFPLClient(bootstrap={"events": [FUTURE_EVENT]})

    with pytest.raises(TeamNotFoundError):
        fetch_current_squad(client, db_session, fpl_team_id=1)  # type: ignore[arg-type]


def test_fetch_current_squad_raises_on_http_error(db_session: Session) -> None:
    client = StubFPLClient(
        bootstrap={"events": [PAST_EVENT]},
        entry={"name": "My Team"},
        picks_error=requests.HTTPError("404"),
    )

    with pytest.raises(TeamNotFoundError):
        fetch_current_squad(client, db_session, fpl_team_id=1)  # type: ignore[arg-type]


def test_fetch_current_squad_maps_picks_to_internal_players(db_session: Session) -> None:
    team = _team(db_session)
    player = _player(db_session, team, fpl_id=555, web_name="Saka")
    client = StubFPLClient(
        bootstrap={"events": [PAST_EVENT]},
        entry={"name": "My Team"},
        picks={
            "picks": [
                {
                    "element": 555,
                    "position": 1,
                    "multiplier": 1,
                    "is_captain": False,
                    "is_vice_captain": False,
                }
            ],
            "entry_history": {"bank": 12},
        },
    )

    result = fetch_current_squad(client, db_session, fpl_team_id=1)  # type: ignore[arg-type]

    assert result.team_name == "My Team"
    assert result.bank == 12
    assert result.event_id == 1
    assert len(result.squad) == 1
    assert result.squad[0].player_id == player.id
    assert result.squad[0].web_name == "Saka"


def test_fetch_current_squad_skips_elements_with_no_matching_player(db_session: Session) -> None:
    client = StubFPLClient(
        bootstrap={"events": [PAST_EVENT]},
        entry={"name": "My Team"},
        picks={"picks": [{"element": 9999}], "entry_history": {"bank": 0}},
    )

    result = fetch_current_squad(client, db_session, fpl_team_id=1)  # type: ignore[arg-type]

    assert result.squad == []


def test_fetch_current_squad_falls_back_to_a_default_name(db_session: Session) -> None:
    client = StubFPLClient(
        bootstrap={"events": [PAST_EVENT]},
        entry={},
        picks={"picks": [], "entry_history": {"bank": 0}},
    )

    result = fetch_current_squad(client, db_session, fpl_team_id=42)  # type: ignore[arg-type]

    assert result.team_name == "Team 42"
