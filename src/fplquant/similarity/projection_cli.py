import argparse
import json
from dataclasses import asdict

from fplquant.models.base import session_scope
from fplquant.similarity.projection import compute_projection
from fplquant.similarity.vectors import build_player_vectors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a 2D PCA/t-SNE projection of player stat vectors as JSON."
    )
    parser.add_argument("--method", choices=["pca", "tsne"], default="pca")
    parser.add_argument("--output", default="player_projection.json")
    args = parser.parse_args()

    with session_scope() as session:
        vectors = build_player_vectors(session)
        projections = compute_projection(vectors, method=args.method)

    with open(args.output, "w") as f:
        json.dump([asdict(p) for p in projections], f, indent=2)

    print(f"Wrote {len(projections)} player projections to {args.output}")


if __name__ == "__main__":
    main()
