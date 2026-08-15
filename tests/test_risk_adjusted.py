import pytest
from sqlalchemy.orm import Session

from fplquant.models.orm import Player, PlayerGameweekStat, Team
from fplquant.risk.adjusted import compute_risk_adjusted_scores


def _team(session: Session) -> Team:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    session.add(team)
    session.flush()
    return team


def _player(session: Session, team: Team, *, fpl_id: int, web_name: str, **kwargs) -> Player:
    player = Player(
        fpl_id=fpl_id,
        team_id=team.id,
        first_name=web_name,
        second_name=web_name,
        web_name=web_name,
        element_type=3,
        now_cost=60,
        status=kwargs.pop("status", "a"),
        ep_next=kwargs.pop("ep_next", 5.0),
        **kwargs,
    )
    session.add(player)
    session.flush()
    return player


def _add_points(session: Session, player: Player, points: list[int]) -> None:
    for round_number, pts in enumerate(points, start=1):
        session.add(PlayerGameweekStat(player_id=player.id, round=round_number, total_points=pts))
    session.flush()


def test_falls_back_to_ep_next_with_no_gameweek_history(db_session: Session) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="NoHistory", ep_next=6.5)

    scores = compute_risk_adjusted_scores(db_session)

    assert len(scores) == 1
    assert scores[0].expected_points == 6.5


def test_no_gameweek_history_means_no_volatility_penalty(db_session: Session) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="NoHistory", ep_next=6.5)

    scores = compute_risk_adjusted_scores(db_session)

    assert scores[0].coefficient_of_variation == 0.0
    assert scores[0].volatility_penalty == 1.0
    # Formula holds regardless of the (nonzero, by design) baseline injury risk
    # a player with unknown age/position defaults still carries.
    score = scores[0]
    assert score.risk_adjusted_points == pytest.approx(
        score.expected_points * score.availability_factor / score.volatility_penalty
    )


def test_currently_injured_player_scores_lower_than_fit_equal_expected_points(
    db_session: Session,
) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="Injured", status="i", ep_next=6.0)
    _player(db_session, team, fpl_id=2, web_name="Fit", status="a", ep_next=6.0)

    scores = {s.web_name: s for s in compute_risk_adjusted_scores(db_session)}

    assert scores["Injured"].risk_adjusted_points < scores["Fit"].risk_adjusted_points
    assert scores["Injured"].availability_factor < scores["Fit"].availability_factor


def test_volatile_player_scores_lower_than_consistent_with_same_mean(db_session: Session) -> None:
    team = _team(db_session)
    volatile = _player(db_session, team, fpl_id=1, web_name="Volatile")
    consistent = _player(db_session, team, fpl_id=2, web_name="Consistent")
    _add_points(db_session, volatile, [0, 12, 0, 12])  # mean 6, high stdev
    _add_points(db_session, consistent, [6, 6, 6, 6])  # mean 6, zero stdev

    scores = {s.web_name: s for s in compute_risk_adjusted_scores(db_session)}

    assert (
        scores["Volatile"].coefficient_of_variation > scores["Consistent"].coefficient_of_variation
    )
    assert scores["Volatile"].risk_adjusted_points < scores["Consistent"].risk_adjusted_points


def test_higher_risk_aversion_penalizes_volatility_more(db_session: Session) -> None:
    team = _team(db_session)
    volatile = _player(db_session, team, fpl_id=1, web_name="Volatile")
    _add_points(db_session, volatile, [0, 12, 0, 12])

    low_aversion = compute_risk_adjusted_scores(db_session, risk_aversion=0.1)[0]
    high_aversion = compute_risk_adjusted_scores(db_session, risk_aversion=5.0)[0]

    assert high_aversion.risk_adjusted_points < low_aversion.risk_adjusted_points


def test_higher_injury_weight_penalizes_injury_risk_more(db_session: Session) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="Injured", status="i", ep_next=6.0)

    low_weight = compute_risk_adjusted_scores(db_session, injury_weight=0.1)[0]
    high_weight = compute_risk_adjusted_scores(db_session, injury_weight=1.0)[0]

    assert high_weight.risk_adjusted_points <= low_weight.risk_adjusted_points


def test_availability_factor_never_negative(db_session: Session) -> None:
    team = _team(db_session)
    _player(
        db_session, team, fpl_id=1, web_name="MaxRisk", status="i", birth_date=None, ep_next=6.0
    )

    scores = compute_risk_adjusted_scores(db_session, injury_weight=10.0)

    assert scores[0].availability_factor >= 0.0


def test_sorted_descending_by_risk_adjusted_points(db_session: Session) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="Low", ep_next=1.0)
    _player(db_session, team, fpl_id=2, web_name="High", ep_next=10.0)

    scores = compute_risk_adjusted_scores(db_session)

    assert [s.web_name for s in scores] == ["High", "Low"]
