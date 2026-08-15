from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fplquant.api import schemas
from fplquant.api.deps import get_session
from fplquant.form.scoring import compute_form_scores

router = APIRouter(tags=["form"])


@router.get("/form", response_model=list[schemas.FormScoreOut])
def get_form_leaderboard(
    top: int = 50, halflife: float = 3.0, session: Session = Depends(get_session)
) -> list[schemas.FormScoreOut]:
    scores = compute_form_scores(session, halflife=halflife)[:top]
    return [schemas.FormScoreOut.model_validate(s) for s in scores]
