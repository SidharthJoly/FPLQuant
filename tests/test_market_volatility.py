import pytest
from sqlalchemy.orm import Session

from fplquant.market.volatility import compute_volatility, compute_volatility_scores
from fplquant.models.orm import Player, PlayerGameweekStat, Team


def test_returns_none_with_fewer_than_two_points() -> None:
    assert compute_volatility("Player", 1, [5]) is None
    assert compute_volatility("Player", 1, []) is None


def test_constant_points_has_zero_stdev() -> None:
    score = compute_volatility("Player", 1, [5, 5, 5, 5])
    assert score is not None
    assert score.points_stdev == 0.0
    assert score.coefficient_of_variation == 0.0


def test_volatile_points_has_higher_stdev_than_consistent() -> None:
    volatile = compute_volatility("Volatile", 1, [0, 15, 1, 12, 0])
    consistent = compute_volatility("Consistent", 2, [5, 6, 5, 6, 5])

    assert volatile is not None
    assert consistent is not None
    assert volatile.points_stdev > consistent.points_stdev


def test_coefficient_of_variation_none_when_mean_zero() -> None:
    score = compute_volatility("Player", 1, [0, 0, 0])
    assert score is not None
    assert score.points_mean == 0.0
    assert score.coefficient_of_variation is None


def test_points_mean_is_correct() -> None:
    score = compute_volatility("Player", 1, [2, 4, 6])
    assert score is not None
    assert score.points_mean == pytest.approx(4.0)


def test_compute_volatility_scores_sorted_descending(db_session: Session) -> None:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    db_session.add(team)
    db_session.flush()

    volatile = Player(
        fpl_id=1,
        team_id=team.id,
        first_name="V",
        second_name="V",
        web_name="Volatile",
        element_type=3,
        now_cost=60,
        status="a",
    )
    steady = Player(
        fpl_id=2,
        team_id=team.id,
        first_name="S",
        second_name="S",
        web_name="Steady",
        element_type=3,
        now_cost=60,
        status="a",
    )
    db_session.add_all([volatile, steady])
    db_session.flush()

    for round_number, pts in enumerate([0, 15, 1, 14], start=1):
        db_session.add(
            PlayerGameweekStat(player_id=volatile.id, round=round_number, total_points=pts)
        )
    for round_number, pts in enumerate([5, 6, 5, 6], start=1):
        db_session.add(
            PlayerGameweekStat(player_id=steady.id, round=round_number, total_points=pts)
        )
    db_session.flush()

    scores = compute_volatility_scores(db_session)

    assert [s.web_name for s in scores] == ["Volatile", "Steady"]
