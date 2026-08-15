from sqlalchemy.orm import Session, selectinload

from fplquant.form.scoring import compute_form_scores
from fplquant.models.orm import Player
from fplquant.optimizer.types import PlayerCandidate

UNAVAILABLE_STATUSES = {"u"}  # unavailable (e.g. left the club / not in FPL this season)


def build_candidates_from_db(
    session: Session, halflife: float = 3.0, exclude_unavailable: bool = True
) -> list[PlayerCandidate]:
    """Build optimizer input from the database.

    Predicted points per player: our own EWMA points_form (from the form module)
    when gameweek history exists, otherwise FPL's own `ep_next` estimate — this
    keeps the optimizer usable before any gameweek history has accumulated (e.g.
    preseason), while preferring our own signal once it's available.
    """
    points_form_by_player = {
        score.player_id: score.points_form for score in compute_form_scores(session, halflife)
    }

    players = session.query(Player).options(selectinload(Player.team)).all()
    candidates = []
    for player in players:
        if exclude_unavailable and player.status in UNAVAILABLE_STATUSES:
            continue
        predicted_points = points_form_by_player.get(player.id, player.ep_next)
        candidates.append(
            PlayerCandidate(
                player_id=player.id,
                web_name=player.web_name,
                team_id=player.team_id,
                team_short_name=player.team.short_name,
                element_type=player.element_type,
                now_cost=player.now_cost,
                predicted_points=predicted_points,
            )
        )
    return candidates
