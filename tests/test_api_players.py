from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from fplquant.models.orm import Player, PlayerGameweekStat, Team


def _team(session: Session, fpl_id: int = 1) -> Team:
    team = Team(fpl_id=fpl_id, name="Arsenal", short_name="ARS")
    session.add(team)
    session.flush()
    return team


def _player(
    session: Session, team: Team, fpl_id: int, web_name: str, element_type: int = 4
) -> Player:
    player = Player(
        fpl_id=fpl_id,
        team_id=team.id,
        first_name=web_name,
        second_name=web_name,
        web_name=web_name,
        element_type=element_type,
        now_cost=80,
        status="a",
        ep_next=5.0,
    )
    session.add(player)
    session.flush()
    return player


def test_list_players_returns_seeded_players(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player(db_session, team, 1, "Striker")
    db_session.commit()

    response = api_client.get("/players")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["web_name"] == "Striker"
    assert body[0]["team_short_name"] == "ARS"


def test_list_players_filters_by_position(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player(db_session, team, 1, "Fwd", element_type=4)
    _player(db_session, team, 2, "Def", element_type=2)
    db_session.commit()

    response = api_client.get("/players", params={"position": 2})

    body = response.json()
    assert [p["web_name"] for p in body] == ["Def"]


def test_list_players_filters_by_search(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player(db_session, team, 1, "Saka")
    _player(db_session, team, 2, "Gabriel")
    db_session.commit()

    response = api_client.get("/players", params={"search": "sak"})

    body = response.json()
    assert [p["web_name"] for p in body] == ["Saka"]


def test_get_player_404_when_missing(api_client: TestClient) -> None:
    response = api_client.get("/players/999")
    assert response.status_code == 404


def test_get_player_detail_includes_none_form_and_risk_when_no_history(
    db_session: Session, api_client: TestClient
) -> None:
    team = _team(db_session)
    player = _player(db_session, team, 1, "NoHistory")
    db_session.commit()

    response = api_client.get(f"/players/{player.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["web_name"] == "NoHistory"
    assert body["form_score"] is None
    assert body["injury_risk"] is not None  # always computable, unlike form


def test_get_player_detail_includes_form_when_history_exists(
    db_session: Session, api_client: TestClient
) -> None:
    team = _team(db_session)
    player = _player(db_session, team, 1, "HasHistory")
    for round_number in range(1, 4):
        db_session.add(PlayerGameweekStat(player_id=player.id, round=round_number, total_points=5))
    db_session.commit()

    response = api_client.get(f"/players/{player.id}")

    body = response.json()
    assert body["form_score"] is not None
    assert body["form_score"]["points_form"] == 5.0


def test_get_player_history_404_when_missing(api_client: TestClient) -> None:
    response = api_client.get("/players/999/history")
    assert response.status_code == 404


def test_get_player_history_returns_gameweek_series(
    db_session: Session, api_client: TestClient
) -> None:
    team = _team(db_session)
    player = _player(db_session, team, 1, "Player")
    for round_number, pts in enumerate([2, 6, 10], start=1):
        db_session.add(
            PlayerGameweekStat(
                player_id=player.id,
                round=round_number,
                total_points=pts,
                minutes=90,
                value=80,
                selected=1000,
            )
        )
    db_session.commit()

    response = api_client.get(f"/players/{player.id}/history")

    assert response.status_code == 200
    body = response.json()
    assert [row["round"] for row in body] == [1, 2, 3]
    assert [row["total_points"] for row in body] == [2, 6, 10]


def test_get_similar_players_404_when_missing(api_client: TestClient) -> None:
    response = api_client.get("/players/999/similar")
    assert response.status_code == 404


def test_get_similar_players_empty_without_gameweek_history(
    db_session: Session, api_client: TestClient
) -> None:
    team = _team(db_session)
    player = _player(db_session, team, 1, "Solo")
    db_session.commit()

    response = api_client.get(f"/players/{player.id}/similar")

    assert response.status_code == 200
    assert response.json() == []
