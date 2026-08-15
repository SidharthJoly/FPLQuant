from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

from fplquant.similarity.vectors import PlayerVector


@dataclass(frozen=True)
class PlayerProjection:
    player_id: int
    web_name: str
    element_type: int
    x: float
    y: float


def _scaled_matrix(vectors: list[PlayerVector]) -> np.ndarray:
    matrix = np.vstack([v.values for v in vectors])
    return StandardScaler().fit_transform(matrix)  # type: ignore[no-any-return]


def compute_pca_projection(vectors: list[PlayerVector]) -> list[PlayerProjection]:
    """2D PCA projection of standardized per-90 stat vectors.

    Fast and deterministic; positions tend to separate out along the first
    couple of components since attacking/defensive stat profiles differ a
    lot, which is a useful visual sanity check.
    """
    if len(vectors) < 2:
        return []
    coords = PCA(n_components=2, random_state=42).fit_transform(_scaled_matrix(vectors))
    return _to_projections(vectors, coords)


def compute_tsne_projection(
    vectors: list[PlayerVector], perplexity: float = 30.0, random_state: int = 42
) -> list[PlayerProjection]:
    """2D t-SNE projection — better than PCA at revealing local clusters of
    similar players, at the cost of being slower and non-deterministic
    between runs with different seeds.
    """
    if len(vectors) < 2:
        return []
    # t-SNE requires perplexity < n_samples; clamp down for small pools.
    effective_perplexity = min(perplexity, len(vectors) - 1)
    coords = TSNE(
        n_components=2, perplexity=effective_perplexity, random_state=random_state
    ).fit_transform(_scaled_matrix(vectors))
    return _to_projections(vectors, coords)


def compute_projection(
    vectors: list[PlayerVector], method: Literal["pca", "tsne"] = "pca"
) -> list[PlayerProjection]:
    if method == "pca":
        return compute_pca_projection(vectors)
    return compute_tsne_projection(vectors)


def _to_projections(vectors: list[PlayerVector], coords: np.ndarray) -> list[PlayerProjection]:
    return [
        PlayerProjection(
            player_id=v.player_id,
            web_name=v.web_name,
            element_type=v.element_type,
            x=float(x),
            y=float(y),
        )
        for v, (x, y) in zip(vectors, coords, strict=True)
    ]
