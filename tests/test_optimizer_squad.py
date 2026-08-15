import pytest

from fplquant.optimizer.squad import optimize_squad
from fplquant.optimizer.types import (
    DEFENDER,
    FORWARD,
    GOALKEEPER,
    MIDFIELDER,
    InfeasibleSquadError,
    PlayerCandidate,
    SquadConstraints,
)


def _pool(
    position: int, team_id: int, count: int, *, cost: int = 40, points: float = 3.0
) -> list[PlayerCandidate]:
    return [
        PlayerCandidate(
            player_id=position * 1000 + team_id * 100 + i,
            web_name=f"P{position}-{team_id}-{i}",
            team_id=team_id,
            team_short_name=f"T{team_id}",
            element_type=position,
            now_cost=cost,
            predicted_points=points,
        )
        for i in range(count)
    ]


def _full_candidate_pool(
    num_teams: int = 6, per_team_per_position: int = 3
) -> list[PlayerCandidate]:
    candidates: list[PlayerCandidate] = []
    for team_id in range(num_teams):
        for position in (GOALKEEPER, DEFENDER, MIDFIELDER, FORWARD):
            candidates += _pool(position, team_id, per_team_per_position)
    return candidates


def test_selects_exactly_squad_size_players() -> None:
    squad = optimize_squad(_full_candidate_pool())
    assert len(squad.players) == 15


def test_respects_position_composition() -> None:
    squad = optimize_squad(_full_candidate_pool())
    counts: dict[int, int] = {}
    for p in squad.players:
        counts[p.element_type] = counts.get(p.element_type, 0) + 1
    assert counts == {GOALKEEPER: 2, DEFENDER: 5, MIDFIELDER: 5, FORWARD: 3}


def test_respects_budget() -> None:
    constraints = SquadConstraints(budget=600)
    squad = optimize_squad(_full_candidate_pool(), constraints)
    assert squad.total_cost <= 600


def test_respects_max_per_club() -> None:
    # Only 3 players per position per club, so max_per_club=3 is already binding
    # once combined with the 15-player squad needing 5+ clubs represented.
    squad = optimize_squad(_full_candidate_pool(num_teams=6, per_team_per_position=3))
    counts: dict[int, int] = {}
    for p in squad.players:
        counts[p.team_id] = counts.get(p.team_id, 0) + 1
    assert all(count <= 3 for count in counts.values())


def test_maximizes_predicted_points_given_equal_cost() -> None:
    candidates = _full_candidate_pool()
    # Make one specific player clearly the best pick in its position/team.
    best = PlayerCandidate(
        player_id=99999,
        web_name="Star",
        team_id=0,
        team_short_name="T0",
        element_type=FORWARD,
        now_cost=40,
        predicted_points=100.0,
    )
    squad = optimize_squad(candidates + [best])
    assert best in squad.players


def test_raises_when_not_enough_players_in_a_position() -> None:
    candidates = _pool(GOALKEEPER, team_id=0, count=1)  # need 2 GKPs, only 1 available
    candidates += _pool(DEFENDER, 1, 5) + _pool(MIDFIELDER, 2, 5) + _pool(FORWARD, 3, 3)
    with pytest.raises(InfeasibleSquadError):
        optimize_squad(candidates)


def test_raises_when_budget_too_low() -> None:
    candidates = _full_candidate_pool()
    with pytest.raises(InfeasibleSquadError):
        optimize_squad(candidates, SquadConstraints(budget=1))


def test_raises_on_empty_candidates() -> None:
    with pytest.raises(InfeasibleSquadError):
        optimize_squad([])


def test_total_cost_and_points_match_selected_players() -> None:
    squad = optimize_squad(_full_candidate_pool())
    assert squad.total_cost == sum(p.now_cost for p in squad.players)
    assert squad.total_predicted_points == pytest.approx(
        sum(p.predicted_points for p in squad.players)
    )
