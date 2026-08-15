from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fplquant.api import schemas
from fplquant.api.deps import get_session
from fplquant.risk.injury import compute_injury_risk_scores

router = APIRouter(tags=["risk"])


@router.get("/risk", response_model=list[schemas.InjuryRiskOut])
def get_risk_leaderboard(
    top: int = 50, session: Session = Depends(get_session)
) -> list[schemas.InjuryRiskOut]:
    scores = compute_injury_risk_scores(session)[:top]
    return [schemas.InjuryRiskOut.model_validate(s) for s in scores]
