import numpy as np

from fplquant.similarity.projection import (
    compute_pca_projection,
    compute_projection,
    compute_tsne_projection,
)
from fplquant.similarity.vectors import FEATURES, PlayerVector


def _vector(player_id: int, web_name: str, **feature_overrides: float) -> PlayerVector:
    values = np.zeros(len(FEATURES))
    for feature, value in feature_overrides.items():
        values[FEATURES.index(feature)] = value
    return PlayerVector(
        player_id=player_id,
        web_name=web_name,
        team_id=1,
        element_type=4,
        now_cost=80,
        total_minutes=900,
        values=values,
    )


def _diverse_pool(n: int = 10) -> list[PlayerVector]:
    return [
        _vector(i, f"P{i}", goals_scored=float(i), assists=float(n - i), threat=float(i * 2))
        for i in range(n)
    ]


def test_pca_returns_one_projection_per_player() -> None:
    vectors = _diverse_pool(5)
    projections = compute_pca_projection(vectors)

    assert len(projections) == 5
    assert {p.player_id for p in projections} == {v.player_id for v in vectors}


def test_pca_returns_empty_for_fewer_than_two_players() -> None:
    assert compute_pca_projection([_vector(1, "Solo", goals_scored=1.0)]) == []
    assert compute_pca_projection([]) == []


def test_tsne_returns_one_projection_per_player() -> None:
    vectors = _diverse_pool(10)
    projections = compute_tsne_projection(vectors, perplexity=3.0)

    assert len(projections) == 10


def test_tsne_clamps_perplexity_for_small_pools_without_raising() -> None:
    vectors = _diverse_pool(4)
    projections = compute_tsne_projection(vectors, perplexity=30.0)

    assert len(projections) == 4


def test_compute_projection_dispatches_by_method() -> None:
    vectors = _diverse_pool(5)
    pca_result = compute_projection(vectors, method="pca")
    tsne_result = compute_projection(vectors, method="tsne")

    assert len(pca_result) == 5
    assert len(tsne_result) == 5
