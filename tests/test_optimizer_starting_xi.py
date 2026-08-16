import pytest

from fplquant.optimizer.starting_xi import select_starting_xi
from fplquant.optimizer.types import (
    DEFENDER,
    FORWARD,
    GOALKEEPER,
    MIDFIELDER,
    InfeasibleSquadError,
    PlayerCandidate,
)


def _player(player_id: int, element_type: int, points: float, team_id: int = 1) -> PlayerCandidate:
    return PlayerCandidate(
        player_id=player_id,
        web_name=f"P{player_id}",
        team_id=team_id,
        team_short_name="T1",
        element_type=element_type,
        now_cost=50,
        predicted_points=points,
    )


def _standard_squad(
    gkp_points: list[float],
    def_points: list[float],
    mid_points: list[float],
    fwd_points: list[float],
) -> list[PlayerCandidate]:
    """Builds a standard 2-5-5-3 squad from explicit per-position point lists."""
    players = []
    pid = 1
    for position, points_list in (
        (GOALKEEPER, gkp_points),
        (DEFENDER, def_points),
        (MIDFIELDER, mid_points),
        (FORWARD, fwd_points),
    ):
        for pts in points_list:
            players.append(_player(pid, position, pts))
            pid += 1
    return players


def test_picks_highest_scoring_formation() -> None:
    # Forwards are much stronger than midfielders here, so a forward-heavy
    # formation (more FWD slots) should beat a midfield-heavy one.
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 4, 4, 4, 4],
        mid_points=[1, 1, 1, 1, 1],
        fwd_points=[10, 10, 10],
    )
    xi = select_starting_xi(squad)

    # 3 forwards is the max allowed by FPL rules; with forwards dominating,
    # the optimizer should use all 3 rather than fielding a weak midfielder.
    assert xi.formation.endswith("-3")


def test_starting_xi_has_eleven_players() -> None:
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[7, 6, 5],
    )
    xi = select_starting_xi(squad)
    assert len(xi.starters) == 11
    assert len(xi.bench) == 4


def test_starting_xi_uses_the_single_best_goalkeeper() -> None:
    squad = _standard_squad(
        gkp_points=[8, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[7, 6, 5],
    )
    xi = select_starting_xi(squad)
    gkp_starters = [p for p in xi.starters if p.element_type == GOALKEEPER]
    assert len(gkp_starters) == 1
    assert gkp_starters[0].predicted_points == 8


def test_bench_goalkeeper_is_the_weaker_one() -> None:
    squad = _standard_squad(
        gkp_points=[8, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[7, 6, 5],
    )
    xi = select_starting_xi(squad)
    bench_gkp = [p for p in xi.bench if p.element_type == GOALKEEPER]
    assert len(bench_gkp) == 1
    assert bench_gkp[0].predicted_points == 3


def test_bench_gkp_is_first_then_outfield_by_points_descending() -> None:
    squad = _standard_squad(
        gkp_points=[8, 3],
        def_points=[10, 3.5, 3, 2.5, 2],  # one def starts, rest could bench
        mid_points=[10, 10, 10, 1, 0.5],
        fwd_points=[10, 10, 0.1],
    )
    xi = select_starting_xi(squad)
    # First bench slot is always the GKP by FPL convention.
    assert xi.bench[0].element_type == GOALKEEPER
    outfield_bench = xi.bench[1:]
    points = [p.predicted_points for p in outfield_bench]
    assert points == sorted(points, reverse=True)


def test_captain_and_vice_captain_are_top_two_starters() -> None:
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[20, 6, 5],  # clear standout
    )
    xi = select_starting_xi(squad)
    assert xi.captain.predicted_points == 20
    assert xi.vice_captain.predicted_points == 6
    assert xi.captain in xi.starters
    assert xi.vice_captain in xi.starters


def test_bench_boost_value_is_sum_of_bench_points() -> None:
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[7, 6, 5],
    )
    xi = select_starting_xi(squad)
    assert xi.bench_boost_value == pytest.approx(sum(p.predicted_points for p in xi.bench))


def test_triple_captain_value_equals_captains_points() -> None:
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[9, 6, 5],
    )
    xi = select_starting_xi(squad)
    assert xi.triple_captain_value == xi.captain.predicted_points


def test_starting_predicted_points_matches_starters_sum() -> None:
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[7, 6, 5],
    )
    xi = select_starting_xi(squad)
    assert xi.starting_predicted_points == pytest.approx(
        sum(p.predicted_points for p in xi.starters)
    )


def test_raises_when_no_goalkeeper() -> None:
    squad = _standard_squad(
        gkp_points=[],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[7, 6, 5],
    )
    with pytest.raises(InfeasibleSquadError):
        select_starting_xi(squad)


def test_raises_when_no_formation_fits() -> None:
    # Zero forwards: every legal formation needs at least 1 FWD.
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4, 3, 3],
        fwd_points=[],
    )
    with pytest.raises(InfeasibleSquadError):
        select_starting_xi(squad)


def test_forced_formation_overrides_the_best_scoring_one() -> None:
    # Forwards dominate here, so the auto-selected formation would end in
    # "-3" (see test_picks_highest_scoring_formation) — forcing 3-5-2 should
    # override that and use only 2 forwards.
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 4, 4, 4, 4],
        mid_points=[1, 1, 1, 1, 1],
        fwd_points=[10, 10, 10],
    )
    xi = select_starting_xi(squad, forced_formation=(3, 5, 2))
    assert xi.formation == "3-5-2"
    fwd_starters = [p for p in xi.starters if p.element_type == FORWARD]
    assert len(fwd_starters) == 2


def test_forced_formation_raises_when_squad_cannot_fill_it() -> None:
    # Only 3 forwards and no formation needs more than 3, but this squad has
    # zero midfielders, so 4-5-1 (needs 5 MID) can't be filled.
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[],
        fwd_points=[7, 6, 5],
    )
    with pytest.raises(InfeasibleSquadError):
        select_starting_xi(squad, forced_formation=(4, 5, 1))


def test_formation_string_format() -> None:
    squad = _standard_squad(
        gkp_points=[5, 3],
        def_points=[4, 3.5, 3, 2.5, 2],
        mid_points=[6, 5.5, 5, 4.5, 4],
        fwd_points=[7, 6, 5],
    )
    xi = select_starting_xi(squad)
    parts = xi.formation.split("-")
    assert len(parts) == 3
    d, m, f = (int(p) for p in parts)
    assert d + m + f == 10
    assert (d, m, f) in [
        (3, 4, 3),
        (3, 5, 2),
        (4, 3, 3),
        (4, 4, 2),
        (4, 5, 1),
        (5, 2, 3),
        (5, 3, 2),
        (5, 4, 1),
    ]
