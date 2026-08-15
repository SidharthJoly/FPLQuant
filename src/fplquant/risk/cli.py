import argparse

from fplquant.models.base import session_scope
from fplquant.risk.injury import compute_injury_risk_scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the FPL Quant injury risk leaderboard.")
    parser.add_argument("--top", type=int, default=20, help="Number of players to show")
    args = parser.parse_args()

    with session_scope() as session:
        scores = compute_injury_risk_scores(session)

    header = f"{'#':>3}  {'Player':<20}{'Age':>6}{'Risk %':>9}"
    print(header)
    print("-" * len(header))
    for rank, score in enumerate(scores[: args.top], start=1):
        age_display = f"{score.age:.1f}" if score.age is not None else "?"
        print(f"{rank:>3}  {score.web_name:<20}{age_display:>6}{score.risk_pct:>9.1f}")


if __name__ == "__main__":
    main()
