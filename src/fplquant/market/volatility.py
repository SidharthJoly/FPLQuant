import statistics
from dataclasses import dataclass

from sqlalchemy.orm import Session, selectinload

from fplquant.models.orm import Player


@dataclass(frozen=True)
class VolatilityScore:
    player_id: int
    web_name: str
    gameweeks_considered: int
    points_mean: float
    points_stdev: float
    coefficient_of_variation: float | None  # stdev / mean; None when mean is 0 (undefined)


def compute_volatility(web_name: str, player_id: int, points: list[int]) -> VolatilityScore | None:
    """Population standard deviation of weekly points — the direct analog of
    return volatility in finance. `coefficient_of_variation` (stdev/mean)
    additionally normalizes for scale, so a volatile bench player and a
    volatile premium forward are comparable. Returns None with fewer than 2
    gameweeks, since variance is undefined for a single point.
    """
    if len(points) < 2:
        return None
    mean = statistics.fmean(points)
    stdev = statistics.pstdev(points)
    return VolatilityScore(
        player_id=player_id,
        web_name=web_name,
        gameweeks_considered=len(points),
        points_mean=mean,
        points_stdev=stdev,
        coefficient_of_variation=(stdev / mean) if mean != 0 else None,
    )


def compute_volatility_scores(session: Session) -> list[VolatilityScore]:
    players = session.query(Player).options(selectinload(Player.gameweek_stats)).all()
    scores = []
    for player in players:
        points = [s.total_points for s in sorted(player.gameweek_stats, key=lambda s: s.round)]
        score = compute_volatility(player.web_name, player.id, points)
        if score is not None:
            scores.append(score)
    return sorted(scores, key=lambda s: s.points_stdev, reverse=True)
