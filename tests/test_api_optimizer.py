from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from fplquant.api import cache as cache_module
from fplquant.api.routers.optimizer import _cache_key
from fplquant.api.schemas import OptimizeRequest
from fplquant.models.orm import Player, Team
from fplquant.optimizer.types import DEFENDER, FORWARD, GOALKEEPER, MIDFIELDER


def _seed_full_pool(session: Session, num_teams: int = 6, per_team_per_position: int = 3) -> None:
    positions = (GOALKEEPER, DEFENDER, MIDFIELDER, FORWARD)
    fpl_id = 1
    for team_index in range(num_teams):
        team = Team(fpl_id=team_index + 1, name=f"Team{team_index}", short_name=f"T{team_index}")
        session.add(team)
        session.flush()
        for position in positions:
            for _ in range(per_team_per_position):
                session.add(
                    Player(
                        fpl_id=fpl_id,
                        team_id=team.id,
                        first_name=f"P{fpl_id}",
                        second_name=f"P{fpl_id}",
                        web_name=f"P{fpl_id}",
                        element_type=position,
                        now_cost=40,
                        status="a",
                        ep_next=3.0,
                    )
                )
                fpl_id += 1
    session.commit()


def test_optimize_returns_valid_squad(db_session: Session, api_client: TestClient) -> None:
    _seed_full_pool(db_session)

    response = api_client.post("/optimize", json={"budget": 100.0, "max_per_club": 3})

    assert response.status_code == 200
    body = response.json()
    assert len(body["squad"]) == 15
    assert body["total_cost"] <= 1000


def test_optimize_infeasible_returns_400(db_session: Session, api_client: TestClient) -> None:
    _seed_full_pool(db_session)

    response = api_client.post("/optimize", json={"budget": 1.0, "max_per_club": 3})

    assert response.status_code == 400
    assert "detail" in response.json()


def test_optimize_risk_adjusted_flag_is_accepted(
    db_session: Session, api_client: TestClient
) -> None:
    _seed_full_pool(db_session)

    response = api_client.post(
        "/optimize",
        json={"budget": 100.0, "max_per_club": 3, "risk_adjusted": True, "risk_aversion": 2.0},
    )

    assert response.status_code == 200
    assert len(response.json()["squad"]) == 15


def test_optimize_result_is_cached_in_redis(db_session: Session, api_client: TestClient) -> None:
    _seed_full_pool(db_session)
    request = {"budget": 100.0, "max_per_club": 3}

    response = api_client.post("/optimize", json=request)
    assert response.status_code == 200

    key = _cache_key(OptimizeRequest(**request))
    cached_value = cache_module.get_client().get(key)
    assert cached_value is not None


def test_optimize_second_identical_request_returns_cached_response(
    db_session: Session, api_client: TestClient
) -> None:
    _seed_full_pool(db_session)
    request = {"budget": 100.0, "max_per_club": 3}

    first = api_client.post("/optimize", json=request).json()
    second = api_client.post("/optimize", json=request).json()

    assert first == second
