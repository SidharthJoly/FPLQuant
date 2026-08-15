import argparse

from fplquant.models.base import session_scope
from fplquant.optimizer.candidates import (
    build_candidates_from_db,
    build_risk_adjusted_candidates_from_db,
)
from fplquant.optimizer.squad import optimize_squad
from fplquant.optimizer.types import POSITION_NAMES, PlayerCandidate, SquadConstraints


def main() -> None:
    parser = argparse.ArgumentParser(description="Select an optimal FPL squad.")
    parser.add_argument(
        "--budget", type=float, default=100.0, help="Budget in millions, e.g. 100.0"
    )
    parser.add_argument("--max-per-club", type=int, default=3)
    parser.add_argument(
        "--risk-adjusted",
        action="store_true",
        help="Maximize risk-adjusted points (form, volatility, injury risk) instead of raw points",
    )
    parser.add_argument(
        "--risk-aversion",
        type=float,
        default=1.0,
        help="Only with --risk-adjusted: higher penalizes volatility more",
    )
    parser.add_argument(
        "--injury-weight",
        type=float,
        default=1.0,
        help="Only with --risk-adjusted: higher penalizes injury risk more",
    )
    args = parser.parse_args()

    constraints = SquadConstraints(budget=round(args.budget * 10), max_per_club=args.max_per_club)

    with session_scope() as session:
        if args.risk_adjusted:
            candidates = build_risk_adjusted_candidates_from_db(
                session, risk_aversion=args.risk_aversion, injury_weight=args.injury_weight
            )
        else:
            candidates = build_candidates_from_db(session)
        squad = optimize_squad(candidates, constraints)

    points_label = "risk-adjusted points" if args.risk_adjusted else "predicted points"
    print(f"Total cost: £{squad.total_cost / 10:.1f}m / £{constraints.budget / 10:.1f}m")
    print(f"Total {points_label}: {squad.total_predicted_points:.2f}")
    print()

    by_position: dict[int, list[PlayerCandidate]] = {}
    for player in squad.players:
        by_position.setdefault(player.element_type, []).append(player)

    for position in sorted(by_position):
        print(f"{POSITION_NAMES[position]}:")
        for player in sorted(by_position[position], key=lambda p: -p.predicted_points):
            print(
                f"  {player.web_name:<20} {player.team_short_name:<4} "
                f"£{player.now_cost / 10:>4.1f}m  {player.predicted_points:>6.2f} pts"
            )


if __name__ == "__main__":
    main()
