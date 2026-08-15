import statistics
from dataclasses import dataclass

from sqlalchemy.orm import Session, selectinload

from fplquant.form.ewma import ewma
from fplquant.models.orm import Player


@dataclass(frozen=True)
class FormScore:
    player_id: int
    web_name: str
    matches_considered: int
    points_form: float
    underlying_form: float
    combined_score: float


def _zscores(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    if stdev == 0:
        return [0.0] * len(values)
    return [(v - mean) / stdev for v in values]


def compute_form_scores(
    session: Session,
    halflife: float = 3.0,
    points_weight: float = 0.7,
    underlying_weight: float = 0.3,
    min_matches: int = 1,
) -> list[FormScore]:
    """Rank players by a blended form score.

    For each player: EWMA of total_points ("points_form") and EWMA of ict_index
    ("underlying_form") are computed from their gameweek history, in chronological
    order. Because points and ict_index live on different scales, each is
    z-scored across the eligible player pool before being combined, so neither
    metric dominates purely because of its raw magnitude — the same technique
    used to blend factors with different units in quant equity models.
    """
    players = session.query(Player).options(selectinload(Player.gameweek_stats)).all()

    eligible: list[Player] = []
    raw_points_form: list[float] = []
    raw_underlying_form: list[float] = []
    matches_by_player: dict[int, int] = {}

    for player in players:
        stats = sorted(player.gameweek_stats, key=lambda s: s.round)
        if len(stats) < min_matches:
            continue
        eligible.append(player)
        matches_by_player[player.id] = len(stats)
        raw_points_form.append(ewma([s.total_points for s in stats], halflife))
        raw_underlying_form.append(ewma([s.ict_index for s in stats], halflife))

    points_z = _zscores(raw_points_form)
    underlying_z = _zscores(raw_underlying_form)

    scores = [
        FormScore(
            player_id=player.id,
            web_name=player.web_name,
            matches_considered=matches_by_player[player.id],
            points_form=raw_points_form[i],
            underlying_form=raw_underlying_form[i],
            combined_score=points_weight * points_z[i] + underlying_weight * underlying_z[i],
        )
        for i, player in enumerate(eligible)
    ]
    return sorted(scores, key=lambda s: s.combined_score, reverse=True)


def predicted_points_by_player(session: Session, halflife: float = 3.0) -> dict[int, float]:
    """Our best current expected-points estimate per player.

    Our own EWMA points_form when gameweek history exists, otherwise FPL's
    own `ep_next` estimate — this keeps downstream consumers (the optimizer,
    the risk-adjusted scorer) usable before any gameweek history has
    accumulated (e.g. preseason), while preferring our own signal once it's
    available.
    """
    points_form_by_player = {
        score.player_id: score.points_form for score in compute_form_scores(session, halflife)
    }
    return {
        player.id: points_form_by_player.get(player.id, player.ep_next)
        for player in session.query(Player).all()
    }
