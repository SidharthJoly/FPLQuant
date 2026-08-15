import argparse

from fplquant.market.correlation import compute_teammate_correlations
from fplquant.market.momentum import compute_price_momentum_scores
from fplquant.market.volatility import compute_volatility_scores
from fplquant.models.base import session_scope


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the FPL Quant stock-market report.")
    parser.add_argument("--top", type=int, default=10, help="Rows per section")
    parser.add_argument("--lookback", type=int, default=5, help="Gameweeks for momentum window")
    args = parser.parse_args()

    with session_scope() as session:
        momentum = compute_price_momentum_scores(session, lookback=args.lookback)
        volatility = compute_volatility_scores(session)
        correlations = compute_teammate_correlations(session)

    print(f"Rising price/ownership (top {args.top}):")
    if not momentum:
        print("  (no gameweek history yet)")
    for m in momentum[: args.top]:
        print(
            f"  {m.web_name:<20} price {m.price_change / 10:+.1f}m ({m.price_change_pct:+.1%})"
            f"  ownership {m.ownership_change_pct:+.1%}  net transfers {m.net_transfers:+d}"
        )

    print(f"\nMost volatile (top {args.top}):")
    if not volatility:
        print("  (no gameweek history yet)")
    for v in volatility[: args.top]:
        print(
            f"  {v.web_name:<20} stdev {v.points_stdev:>5.2f}  mean {v.points_mean:>5.2f}"
            f"  ({v.gameweeks_considered} GWs)"
        )

    print(f"\nMost correlated teammates (top {args.top}) — lowest diversification:")
    if not correlations:
        print("  (no gameweek history yet)")
    for c in correlations[: args.top]:
        print(
            f"  {c.player_a_web_name:<15} <-> {c.player_b_web_name:<15}"
            f"  r={c.correlation:+.2f}  ({c.overlap_gameweeks} shared GWs)"
        )


if __name__ == "__main__":
    main()
