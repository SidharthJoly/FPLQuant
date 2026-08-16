from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from fplquant.models.orm import Player, PlayerGameweekStat, Team


def _team(session: Session) -> Team:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    session.add(team)
    session.flush()
    return team


def _player_with_history(session: Session, team: Team, fpl_id: int, web_name: str) -> Player:
    player = Player(
        fpl_id=fpl_id,
        team_id=team.id,
        first_name=web_name,
        second_name=web_name,
        web_name=web_name,
        element_type=4,
        now_cost=80,
        status="a",
    )
    session.add(player)
    session.flush()
    for round_number, pts in enumerate([2, 6, 10], start=1):
        session.add(
            PlayerGameweekStat(
                player_id=player.id,
                round=round_number,
                total_points=pts,
                value=80 + round_number,
                selected=1000 + round_number * 10,
            )
        )
    session.commit()
    return player


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_form_endpoint(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player_with_history(db_session, team, 1, "Rising")

    response = api_client.get("/form")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["web_name"] == "Rising"


def test_risk_endpoint(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player_with_history(db_session, team, 1, "Player")

    response = api_client.get("/risk")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_market_momentum_endpoint(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player_with_history(db_session, team, 1, "Player")

    response = api_client.get("/market/momentum")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["price_change"] == 2  # value 81 -> 83 over 3 gameweeks
    assert body[0]["team_short_name"] == "ARS"


def test_market_volatility_endpoint(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player_with_history(db_session, team, 1, "Player")

    response = api_client.get("/market/volatility")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_market_correlation_endpoint(db_session: Session, api_client: TestClient) -> None:
    team = _team(db_session)
    _player_with_history(db_session, team, 1, "PlayerA")
    _player_with_history(db_session, team, 2, "PlayerB")

    response = api_client.get("/market/correlation", params={"min_overlap": 2})

    assert response.status_code == 200
    assert len(response.json()) == 1
