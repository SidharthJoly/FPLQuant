from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from fplquant.api import schemas
from fplquant.api.deps import get_session
from fplquant.data.fpl_client import FPLClient
from fplquant.market.correlation import compute_teammate_correlations
from fplquant.market.momentum import compute_live_market_movers, compute_price_momentum_scores
from fplquant.market.volatility import compute_volatility_scores
from fplquant.models.orm import Player

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/momentum", response_model=list[schemas.PriceMomentumOut])
def get_momentum(
    top: int = 20, lookback: int = 5, session: Session = Depends(get_session)
) -> list[schemas.PriceMomentumOut]:
    scores = compute_price_momentum_scores(session, lookback=lookback)[:top]

    if not scores:
        # Not enough finished-gameweek history yet (early season, or between
        # gameweeks before FPL finalizes bonus points) — fall back to FPL's
        # live daily fields so the ticker still moves day to day.
        with FPLClient() as client:
            bootstrap = client.get_bootstrap_static()
        players_by_fpl_id = {p.fpl_id: p for p in session.query(Player).all()}
        scores = compute_live_market_movers(
            bootstrap["elements"], players_by_fpl_id, bootstrap.get("total_players", 0)
        )[:top]

    teams_by_player_id = {
        p.id: p.team.short_name
        for p in session.query(Player)
        .options(selectinload(Player.team))
        .filter(Player.id.in_([s.player_id for s in scores]))
        .all()
    }
    return [
        schemas.PriceMomentumOut(
            player_id=s.player_id,
            web_name=s.web_name,
            team_short_name=teams_by_player_id.get(s.player_id, ""),
            gameweeks_considered=s.gameweeks_considered,
            price_change=s.price_change,
            price_change_pct=s.price_change_pct,
            net_transfers=s.net_transfers,
            ownership_change=s.ownership_change,
            ownership_change_pct=s.ownership_change_pct,
        )
        for s in scores
    ]


@router.get("/volatility", response_model=list[schemas.VolatilityScoreOut])
def get_volatility(
    top: int = 20, session: Session = Depends(get_session)
) -> list[schemas.VolatilityScoreOut]:
    scores = compute_volatility_scores(session)[:top]
    return [schemas.VolatilityScoreOut.model_validate(s) for s in scores]


@router.get("/correlation", response_model=list[schemas.TeammateCorrelationOut])
def get_correlation(
    top: int = 20, min_overlap: int = 3, session: Session = Depends(get_session)
) -> list[schemas.TeammateCorrelationOut]:
    scores = compute_teammate_correlations(session, min_overlap=min_overlap)[:top]
    return [schemas.TeammateCorrelationOut.model_validate(s) for s in scores]
