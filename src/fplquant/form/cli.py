import argparse

from fplquant.form.scoring import compute_form_scores
from fplquant.models.base import session_scope


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the FPL Quant form leaderboard.")
    parser.add_argument("--top", type=int, default=20, help="Number of players to show")
    parser.add_argument("--halflife", type=float, default=3.0, help="EWMA halflife, in gameweeks")
    args = parser.parse_args()

    with session_scope() as session:
        scores = compute_form_scores(session, halflife=args.halflife)

    header = (
        f"{'#':>3}  {'Player':<20}{'GWs':>5}{'Points form':>14}{'Underlying':>12}{'Combined':>10}"
    )
    print(header)
    print("-" * len(header))
    for rank, score in enumerate(scores[: args.top], start=1):
        print(
            f"{rank:>3}  {score.web_name:<20}{score.matches_considered:>5}"
            f"{score.points_form:>14.2f}{score.underlying_form:>12.2f}"
            f"{score.combined_score:>10.2f}"
        )


if __name__ == "__main__":
    main()
