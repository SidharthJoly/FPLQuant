import hashlib

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fplquant.api import schemas
from fplquant.api.cache import cache_get, cache_set
from fplquant.api.deps import get_session
from fplquant.config import settings
from fplquant.optimizer.candidates import (
    build_candidates_from_db,
    build_risk_adjusted_candidates_from_db,
)
from fplquant.optimizer.squad import optimize_squad
from fplquant.optimizer.types import SquadConstraints

router = APIRouter(tags=["optimizer"])


def _cache_key(request: schemas.OptimizeRequest) -> str:
    payload = request.model_dump_json()
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"fplquant:optimize:{digest}"


@router.post("/optimize", response_model=schemas.OptimizeResponse)
def optimize(
    request: schemas.OptimizeRequest, session: Session = Depends(get_session)
) -> schemas.OptimizeResponse:
    """Select an optimal squad. Results are cached in Redis (keyed on the
    request parameters) since the ILP solve — and, for risk_adjusted
    requests, the underlying form/volatility/injury-risk computations — are
    the most expensive operations this API performs.
    """
    cache_key = _cache_key(request)
    cached = cache_get(cache_key)
    if cached is not None:
        return schemas.OptimizeResponse.model_validate_json(cached)

    constraints = SquadConstraints(
        budget=round(request.budget * 10), max_per_club=request.max_per_club
    )
    if request.risk_adjusted:
        candidates = build_risk_adjusted_candidates_from_db(
            session, risk_aversion=request.risk_aversion, injury_weight=request.injury_weight
        )
    else:
        candidates = build_candidates_from_db(session)

    squad = optimize_squad(candidates, constraints)
    response = schemas.OptimizeResponse(
        total_cost=squad.total_cost,
        total_predicted_points=squad.total_predicted_points,
        squad=[schemas.SquadPlayerOut.model_validate(p) for p in squad.players],
    )

    cache_set(cache_key, response.model_dump_json(), settings.optimize_cache_ttl_seconds)
    return response
