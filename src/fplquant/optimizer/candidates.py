from sqlalchemy.orm import Session, selectinload

from fplquant.form.fixtures import FixtureAdjustedScore, compute_fixture_adjusted_scores
from fplquant.models.orm import Player
from fplquant.optimizer.types import PlayerCandidate
from fplquant.risk.adjusted import compute_risk_adjusted_scores

UNAVAILABLE_STATUSES = {"u"}  # unavailable (e.g. left the club / not in FPL this season)


def _candidates_from_points(
    session: Session,
    points_by_player: dict[int, float],
    exclude_unavailable: bool,
    fixtures_by_player: dict[int, FixtureAdjustedScore] | None = None,
) -> list[PlayerCandidate]:
    players = session.query(Player).options(selectinload(Player.team)).all()
    fixtures_by_player = fixtures_by_player or {}
    candidates = []
    for player in players:
        if exclude_unavailable and player.status in UNAVAILABLE_STATUSES:
            continue
        fixture = fixtures_by_player.get(player.id)
        candidates.append(
            PlayerCandidate(
                player_id=player.id,
                web_name=player.web_name,
                team_id=player.team_id,
                team_short_name=player.team.short_name,
                element_type=player.element_type,
                now_cost=player.now_cost,
                predicted_points=points_by_player.get(player.id, 0.0),
                next_opponent=fixture.opponent_short_name if fixture else None,
                next_opponent_is_home=fixture.is_home if fixture else None,
                fixture_difficulty=fixture.difficulty if fixture else None,
                chance_of_playing=fixture.chance_of_playing if fixture else 1.0,
            )
        )
    return candidates


def build_candidates_from_db(
    session: Session, halflife: float = 3.0, exclude_unavailable: bool = True
) -> list[PlayerCandidate]:
    """Build optimizer input from the database, maximizing fixture-adjusted
    expected points for each player's next match.

    See `fplquant.form.fixtures.compute_fixture_adjusted_scores` for how
    points are predicted: season-form EWMA, adjusted for opponent strength,
    home/away venue, and the chance the player actually plays. For a
    risk-adjusted alternative, see
    `fplquant.optimizer.candidates.build_risk_adjusted_candidates_from_db`.
    """
    fixtures_by_player = {
        s.player_id: s for s in compute_fixture_adjusted_scores(session, halflife)
    }
    points_by_player = {pid: s.adjusted_points for pid, s in fixtures_by_player.items()}
    return _candidates_from_points(
        session, points_by_player, exclude_unavailable, fixtures_by_player
    )


def build_risk_adjusted_candidates_from_db(
    session: Session,
    halflife: float = 3.0,
    risk_aversion: float = 1.0,
    injury_weight: float = 1.0,
    exclude_unavailable: bool = True,
) -> list[PlayerCandidate]:
    """Build optimizer input maximizing risk-adjusted expected points instead
    of raw predicted points — see `fplquant.risk.adjusted.compute_risk_adjusted_scores`
    for how volatility and injury risk are folded in.
    """
    fixtures_by_player = {
        s.player_id: s for s in compute_fixture_adjusted_scores(session, halflife)
    }
    points_by_player = {
        s.player_id: s.risk_adjusted_points
        for s in compute_risk_adjusted_scores(session, halflife, risk_aversion, injury_weight)
    }
    return _candidates_from_points(
        session, points_by_player, exclude_unavailable, fixtures_by_player
    )
