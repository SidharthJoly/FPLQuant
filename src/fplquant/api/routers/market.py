from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fplquant.api import schemas
from fplquant.api.deps import get_session
from fplquant.market.correlation import compute_teammate_correlations
from fplquant.market.momentum import compute_price_momentum_scores
from fplquant.market.volatility import compute_volatility_scores

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/momentum", response_model=list[schemas.PriceMomentumOut])
def get_momentum(
    top: int = 20, lookback: int = 5, session: Session = Depends(get_session)
) -> list[schemas.PriceMomentumOut]:
    scores = compute_price_momentum_scores(session, lookback=lookback)[:top]
    return [schemas.PriceMomentumOut.model_validate(s) for s in scores]


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
