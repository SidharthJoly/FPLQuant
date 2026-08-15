from dataclasses import dataclass

from sqlalchemy.orm import Session, selectinload

from fplquant.models.orm import Player, PlayerGameweekStat


@dataclass(frozen=True)
class PriceMomentum:
    player_id: int
    web_name: str
    gameweeks_considered: int
    price_change: int  # tenths of a million, e.g. 3 = +£0.3m
    price_change_pct: float
    net_transfers: int  # sum(transfers_in - transfers_out) over the window
    ownership_change: int  # change in total managers owning the player
    ownership_change_pct: float


def compute_price_momentum(
    web_name: str, stats: list[PlayerGameweekStat], lookback: int = 5
) -> PriceMomentum | None:
    """Momentum over the most recent `lookback` gameweeks (or fewer if unavailable).

    Mirrors classic price/volume momentum indicators: the change in price and
    ownership over the window, plus net transfer flow (in - out) as an
    "order flow" signal. Returns None with fewer than 2 gameweeks of history,
    since there's nothing to compute a change over.
    """
    window = sorted(stats, key=lambda s: s.round)[-lookback:]
    if len(window) < 2:
        return None

    first, last = window[0], window[-1]
    price_change = last.value - first.value
    price_change_pct = price_change / first.value if first.value else 0.0
    ownership_change = last.selected - first.selected
    ownership_change_pct = ownership_change / first.selected if first.selected else 0.0
    net_transfers = sum(s.transfers_in - s.transfers_out for s in window)

    return PriceMomentum(
        player_id=first.player_id,
        web_name=web_name,
        gameweeks_considered=len(window),
        price_change=price_change,
        price_change_pct=price_change_pct,
        net_transfers=net_transfers,
        ownership_change=ownership_change,
        ownership_change_pct=ownership_change_pct,
    )


def compute_price_momentum_scores(session: Session, lookback: int = 5) -> list[PriceMomentum]:
    players = session.query(Player).options(selectinload(Player.gameweek_stats)).all()
    scores = []
    for player in players:
        momentum = compute_price_momentum(player.web_name, player.gameweek_stats, lookback)
        if momentum is not None:
            scores.append(momentum)
    return sorted(scores, key=lambda m: m.price_change_pct, reverse=True)
