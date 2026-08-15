import argparse
import sys

from sqlalchemy.orm import Session

from fplquant.models.base import session_scope
from fplquant.models.orm import Player
from fplquant.similarity.finder import find_cheaper_alternatives, find_similar_players
from fplquant.similarity.vectors import build_player_vectors


def _resolve_player(session: Session, name: str) -> Player | None:
    matches = session.query(Player).filter(Player.web_name.ilike(f"%{name}%")).all()
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Multiple players match '{name}':", file=sys.stderr)
        for p in matches:
            print(f"  {p.web_name} ({p.team.short_name})", file=sys.stderr)
        print("Be more specific.", file=sys.stderr)
    else:
        print(f"No player found matching '{name}'.", file=sys.stderr)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Find players with a similar playing style.")
    parser.add_argument("player", help="Player name (or substring), e.g. 'Salah'")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument(
        "--cheaper-only", action="store_true", help="Only show cheaper same-position players"
    )
    parser.add_argument(
        "--any-position", action="store_true", help="Don't restrict to the same position"
    )
    args = parser.parse_args()

    with session_scope() as session:
        player = _resolve_player(session, args.player)
        if player is None:
            sys.exit(1)

        vectors = build_player_vectors(session)
        if args.cheaper_only:
            results = find_cheaper_alternatives(vectors, player.id, k=args.top)
        else:
            results = find_similar_players(
                vectors,
                player.id,
                k=args.top,
                same_position_only=not args.any_position,
            )

        print(f"Players most similar to {player.web_name} ({player.team.short_name}):")
        if not results:
            print("  (no gameweek history yet, or no matching candidates)")
        for r in results:
            print(f"  {r.web_name:<20} £{r.now_cost / 10:>4.1f}m  similarity {r.similarity:+.2f}")


if __name__ == "__main__":
    main()
