from dataclasses import dataclass

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from fplquant.similarity.vectors import PlayerVector


@dataclass(frozen=True)
class SimilarPlayer:
    player_id: int
    web_name: str
    team_id: int
    now_cost: int
    similarity: float


def find_similar_players(
    vectors: list[PlayerVector],
    target_player_id: int,
    k: int = 5,
    same_position_only: bool = True,
    cheaper_only: bool = False,
) -> list[SimilarPlayer]:
    """k-NN lookup by cosine similarity of per-90 stat vectors.

    Features are standardized (z-scored) across the comparison pool before
    computing similarity, so no single high-magnitude stat (e.g. bps) drowns
    out the others — the same normalize-before-combine approach used
    elsewhere in this project (form scoring, risk scoring).
    """
    target = next((v for v in vectors if v.player_id == target_player_id), None)
    if target is None:
        return []

    candidates = [
        v
        for v in vectors
        if v.player_id != target_player_id
        and (v.element_type == target.element_type if same_position_only else True)
        and (v.now_cost < target.now_cost if cheaper_only else True)
    ]
    if not candidates:
        return []

    pool = np.vstack([target.values] + [c.values for c in candidates])
    scaled = StandardScaler().fit_transform(pool)
    target_scaled, candidate_scaled = scaled[:1], scaled[1:]

    similarities = cosine_similarity(target_scaled, candidate_scaled)[0]
    ranked = sorted(
        zip(candidates, similarities, strict=True), key=lambda pair: pair[1], reverse=True
    )

    return [
        SimilarPlayer(
            player_id=c.player_id,
            web_name=c.web_name,
            team_id=c.team_id,
            now_cost=c.now_cost,
            similarity=float(sim),
        )
        for c, sim in ranked[:k]
    ]


def find_cheaper_alternatives(
    vectors: list[PlayerVector], target_player_id: int, k: int = 5
) -> list[SimilarPlayer]:
    """Same-position players with a similar playing style who cost less."""
    return find_similar_players(
        vectors, target_player_id, k=k, same_position_only=True, cheaper_only=True
    )
