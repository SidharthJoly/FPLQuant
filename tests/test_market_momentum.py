import pytest
from sqlalchemy.orm import Session

from fplquant.market.momentum import (
    compute_live_market_movers,
    compute_price_momentum,
    compute_price_momentum_scores,
)
from fplquant.models.orm import Player, PlayerGameweekStat, Team


def _stat(
    round_number: int, value: int, selected: int, transfers_in: int = 0, transfers_out: int = 0
) -> PlayerGameweekStat:
    return PlayerGameweekStat(
        player_id=1,
        round=round_number,
        value=value,
        selected=selected,
        transfers_in=transfers_in,
        transfers_out=transfers_out,
    )


def test_returns_none_with_fewer_than_two_gameweeks() -> None:
    assert compute_price_momentum("Player", [_stat(1, 100, 1000)]) is None


def test_returns_none_with_no_gameweeks() -> None:
    assert compute_price_momentum("Player", []) is None


def test_computes_price_and_ownership_change() -> None:
    stats = [_stat(1, 100, 1000), _stat(2, 105, 1200), _stat(3, 110, 900)]
    momentum = compute_price_momentum("Player", stats, lookback=5)

    assert momentum is not None
    assert momentum.price_change == 10
    assert momentum.price_change_pct == 0.1
    assert momentum.ownership_change == -100
    assert momentum.ownership_change_pct == pytest.approx(-0.1)


def test_lookback_limits_window() -> None:
    stats = [_stat(i, 100 + i, 1000) for i in range(1, 11)]  # rounds 1..10, value 101..110
    momentum = compute_price_momentum("Player", stats, lookback=3)

    assert momentum is not None
    assert momentum.gameweeks_considered == 3
    # last 3 rounds: 8,9,10 -> values 108,109,110
    assert momentum.price_change == 2


def test_net_transfers_sums_window() -> None:
    stats = [
        _stat(1, 100, 1000, transfers_in=5000, transfers_out=1000),
        _stat(2, 100, 1000, transfers_in=3000, transfers_out=500),
    ]
    momentum = compute_price_momentum("Player", stats, lookback=5)

    assert momentum is not None
    assert momentum.net_transfers == (5000 - 1000) + (3000 - 500)


def test_handles_zero_starting_value_and_ownership_without_dividing_by_zero() -> None:
    stats = [_stat(1, 0, 0), _stat(2, 5, 10)]
    momentum = compute_price_momentum("Player", stats, lookback=5)

    assert momentum is not None
    assert momentum.price_change_pct == 0.0
    assert momentum.ownership_change_pct == 0.0


def test_compute_price_momentum_scores_sorted_descending(db_session: Session) -> None:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    db_session.add(team)
    db_session.flush()

    rising = Player(
        fpl_id=1,
        team_id=team.id,
        first_name="R",
        second_name="R",
        web_name="Rising",
        element_type=3,
        now_cost=60,
        status="a",
    )
    falling = Player(
        fpl_id=2,
        team_id=team.id,
        first_name="F",
        second_name="F",
        web_name="Falling",
        element_type=3,
        now_cost=60,
        status="a",
    )
    db_session.add_all([rising, falling])
    db_session.flush()

    db_session.add_all(
        [
            PlayerGameweekStat(player_id=rising.id, round=1, value=100, selected=1000),
            PlayerGameweekStat(player_id=rising.id, round=2, value=120, selected=1000),
            PlayerGameweekStat(player_id=falling.id, round=1, value=100, selected=1000),
            PlayerGameweekStat(player_id=falling.id, round=2, value=80, selected=1000),
        ]
    )
    db_session.flush()

    scores = compute_price_momentum_scores(db_session)

    assert [s.web_name for s in scores] == ["Rising", "Falling"]


def test_live_market_movers_uses_bootstrap_fields_without_gameweek_history() -> None:
    riser = Player(
        id=1,
        fpl_id=101,
        team_id=1,
        first_name="R",
        second_name="R",
        web_name="Riser",
        element_type=3,
        now_cost=100,
        status="a",
    )
    faller = Player(
        id=2,
        fpl_id=102,
        team_id=1,
        first_name="F",
        second_name="F",
        web_name="Faller",
        element_type=3,
        now_cost=100,
        status="a",
    )
    quiet = Player(
        id=3,
        fpl_id=103,
        team_id=1,
        first_name="Q",
        second_name="Q",
        web_name="Quiet",
        element_type=3,
        now_cost=100,
        status="a",
    )
    players_by_fpl_id = {101: riser, 102: faller, 103: quiet}

    elements = [
        {
            "id": 101,
            "cost_change_event": 1,
            "transfers_in_event": 50000,
            "transfers_out_event": 1000,
        },
        {
            "id": 102,
            "cost_change_event": -1,
            "transfers_in_event": 1000,
            "transfers_out_event": 40000,
        },
        {"id": 103, "cost_change_event": 0, "transfers_in_event": 0, "transfers_out_event": 0},
        {"id": 999, "cost_change_event": 2, "transfers_in_event": 10000, "transfers_out_event": 0},
    ]

    scores = compute_live_market_movers(elements, players_by_fpl_id, total_players=1_000_000)

    # Quiet (no movement) and the unknown fpl_id (999, not in our DB) are dropped.
    assert [s.web_name for s in scores] == ["Riser", "Faller"]
    assert scores[0].price_change == 1
    assert scores[0].net_transfers == 49000
    assert scores[1].price_change == -1
