import pytest
from sqlalchemy.orm import Session

from fplquant.market.correlation import compute_teammate_correlations
from fplquant.models.orm import Player, PlayerGameweekStat, Team


def _team(session: Session, fpl_id: int = 1) -> Team:
    team = Team(fpl_id=fpl_id, name="Arsenal", short_name="ARS")
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
        now_cost=60,
        status="a",
    )
    session.add(player)
    session.flush()
    return player


def _add_points(session: Session, player: Player, points: list[int]) -> None:
    for round_number, pts in enumerate(points, start=1):
        session.add(PlayerGameweekStat(player_id=player.id, round=round_number, total_points=pts))
    session.flush()


def test_perfectly_correlated_teammates(db_session: Session) -> None:
    team = _team(db_session)
    a = _player(db_session, team, 1, "A")
    b = _player(db_session, team, 2, "B")
    _add_points(db_session, a, [2, 4, 6, 8])
    _add_points(db_session, b, [1, 2, 3, 4])  # perfectly proportional

    results = compute_teammate_correlations(db_session, min_overlap=3)

    assert len(results) == 1
    assert results[0].correlation == pytest.approx(1.0)


def test_anticorrelated_teammates(db_session: Session) -> None:
    team = _team(db_session)
    a = _player(db_session, team, 1, "A")
    b = _player(db_session, team, 2, "B")
    _add_points(db_session, a, [10, 8, 6, 4])
    _add_points(db_session, b, [1, 3, 5, 7])

    results = compute_teammate_correlations(db_session, min_overlap=3)

    assert len(results) == 1
    assert results[0].correlation < 0


def test_different_teams_are_not_compared(db_session: Session) -> None:
    team_a = _team(db_session, fpl_id=1)
    team_b = _team(db_session, fpl_id=2)
    p1 = _player(db_session, team_a, 1, "P1")
    p2 = _player(db_session, team_b, 2, "P2")
    _add_points(db_session, p1, [1, 2, 3, 4])
    _add_points(db_session, p2, [1, 2, 3, 4])

    results = compute_teammate_correlations(db_session)

    assert results == []


def test_skips_pairs_below_min_overlap(db_session: Session) -> None:
    team = _team(db_session)
    a = _player(db_session, team, 1, "A")
    b = _player(db_session, team, 2, "B")
    _add_points(db_session, a, [1, 2])  # only 2 shared gameweeks
    _add_points(db_session, b, [3, 4])

    results = compute_teammate_correlations(db_session, min_overlap=3)

    assert results == []


def test_skips_pairs_with_zero_variance(db_session: Session) -> None:
    team = _team(db_session)
    a = _player(db_session, team, 1, "A")
    b = _player(db_session, team, 2, "Constant")
    _add_points(db_session, a, [1, 5, 2, 8])
    _add_points(db_session, b, [3, 3, 3, 3])  # zero variance -> undefined correlation

    results = compute_teammate_correlations(db_session, min_overlap=3)

    assert results == []


def test_only_uses_overlapping_rounds(db_session: Session) -> None:
    team = _team(db_session)
    a = _player(db_session, team, 1, "A")
    b = _player(db_session, team, 2, "B")
    # a has rounds 1-4, b only has rounds 2-4 (e.g. joined the club mid-season)
    _add_points(db_session, a, [100, 2, 4, 6])  # round 1 = 100 (outlier, not shared)
    db_session.add(PlayerGameweekStat(player_id=b.id, round=2, total_points=1))
    db_session.add(PlayerGameweekStat(player_id=b.id, round=3, total_points=2))
    db_session.add(PlayerGameweekStat(player_id=b.id, round=4, total_points=3))
    db_session.flush()

    results = compute_teammate_correlations(db_session, min_overlap=3)

    assert len(results) == 1
    assert results[0].overlap_gameweeks == 3
    assert results[0].correlation == pytest.approx(1.0)
