from sqlalchemy.orm import Session, selectinload

from fplquant.form.scoring import predicted_points_by_player
from fplquant.models.orm import Player
from fplquant.optimizer.types import PlayerCandidate
from fplquant.risk.adjusted import compute_risk_adjusted_scores

UNAVAILABLE_STATUSES = {"u"}  # unavailable (e.g. left the club / not in FPL this season)


def _candidates_from_points(
    session: Session, points_by_player: dict[int, float], exclude_unavailable: bool
) -> list[PlayerCandidate]:
    players = session.query(Player).options(selectinload(Player.team)).all()
    candidates = []
    for player in players:
        if exclude_unavailable and player.status in UNAVAILABLE_STATUSES:
            continue
        candidates.append(
            PlayerCandidate(
                player_id=player.id,
                web_name=player.web_name,
                team_id=player.team_id,
                team_short_name=player.team.short_name,
                element_type=player.element_type,
                now_cost=player.now_cost,
                predicted_points=points_by_player.get(player.id, 0.0),
            )
        )
    return candidates


def build_candidates_from_db(
    session: Session, halflife: float = 3.0, exclude_unavailable: bool = True
) -> list[PlayerCandidate]:
    """Build optimizer input from the database, maximizing raw predicted points.

    See `fplquant.form.scoring.predicted_points_by_player` for how points are
    predicted. For a risk-adjusted alternative, see
    `fplquant.optimizer.candidates.build_risk_adjusted_candidates_from_db`.
    """
    points_by_player = predicted_points_by_player(session, halflife)
    return _candidates_from_points(session, points_by_player, exclude_unavailable)


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
    points_by_player = {
        s.player_id: s.risk_adjusted_points
        for s in compute_risk_adjusted_scores(session, halflife, risk_aversion, injury_weight)
    }
    return _candidates_from_points(session, points_by_player, exclude_unavailable)
