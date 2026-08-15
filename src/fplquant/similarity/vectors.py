from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session, selectinload

from fplquant.models.orm import Player

# Per-90 features used to represent a player's playing style. Excludes minutes,
# price, and ownership — this vector is about *what a player does on the
# pitch*, not their cost or popularity (those are handled separately by the
# optimizer and market modules).
FEATURES = [
    "goals_scored",
    "assists",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "clean_sheets",
    "goals_conceded",
    "expected_goals_conceded",
    "bonus",
    "bps",
    "influence",
    "creativity",
    "threat",
    "ict_index",
]


@dataclass(frozen=True)
class PlayerVector:
    player_id: int
    web_name: str
    team_id: int
    element_type: int
    now_cost: int
    total_minutes: int
    values: np.ndarray  # per-90 values, in FEATURES order


def compute_player_vector(player: Player) -> PlayerVector | None:
    """Season-aggregate per-90 stat vector for `player`.

    Returns None if the player has no minutes on record yet — a per-90 rate
    is undefined with a zero denominator.
    """
    stats = player.gameweek_stats
    total_minutes = sum(s.minutes for s in stats)
    if total_minutes == 0:
        return None

    totals = np.array([sum(getattr(s, feature) for s in stats) for feature in FEATURES])
    per_90 = totals / total_minutes * 90

    return PlayerVector(
        player_id=player.id,
        web_name=player.web_name,
        team_id=player.team_id,
        element_type=player.element_type,
        now_cost=player.now_cost,
        total_minutes=total_minutes,
        values=per_90,
    )


def build_player_vectors(session: Session) -> list[PlayerVector]:
    players = session.query(Player).options(selectinload(Player.gameweek_stats)).all()
    vectors = (compute_player_vector(p) for p in players)
    return [v for v in vectors if v is not None]
