from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from fplquant.api import schemas
from fplquant.api.deps import get_session
from fplquant.form.scoring import compute_form_scores
from fplquant.models.orm import Player
from fplquant.risk.injury import compute_injury_risk_scores
from fplquant.similarity.finder import find_cheaper_alternatives, find_similar_players
from fplquant.similarity.vectors import build_player_vectors

router = APIRouter(prefix="/players", tags=["players"])


def _to_player_out(player: Player) -> schemas.PlayerOut:
    return schemas.PlayerOut(
        id=player.id,
        fpl_id=player.fpl_id,
        web_name=player.web_name,
        team_id=player.team_id,
        team_short_name=player.team.short_name,
        element_type=player.element_type,
        now_cost=player.now_cost,
        status=player.status,
        selected_by_percent=player.selected_by_percent,
        form=player.form,
        ep_next=player.ep_next,
    )


@router.get("", response_model=list[schemas.PlayerOut])
def list_players(
    position: int | None = None,
    team_id: int | None = None,
    max_cost: int | None = None,
    search: str | None = None,
    session: Session = Depends(get_session),
) -> list[schemas.PlayerOut]:
    query = session.query(Player).options(selectinload(Player.team))
    if position is not None:
        query = query.filter(Player.element_type == position)
    if team_id is not None:
        query = query.filter(Player.team_id == team_id)
    if max_cost is not None:
        query = query.filter(Player.now_cost <= max_cost)
    if search:
        query = query.filter(Player.web_name.ilike(f"%{search}%"))
    return [_to_player_out(p) for p in query.all()]


@router.get("/{player_id}", response_model=schemas.PlayerDetailOut)
def get_player(player_id: int, session: Session = Depends(get_session)) -> schemas.PlayerDetailOut:
    player = session.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    form = next((s for s in compute_form_scores(session) if s.player_id == player_id), None)
    risk = next((s for s in compute_injury_risk_scores(session) if s.player_id == player_id), None)

    return schemas.PlayerDetailOut(
        **_to_player_out(player).model_dump(),
        form_score=schemas.FormScoreOut.model_validate(form) if form else None,
        injury_risk=schemas.InjuryRiskOut.model_validate(risk) if risk else None,
    )


@router.get("/{player_id}/similar", response_model=list[schemas.SimilarPlayerOut])
def get_similar_players(
    player_id: int,
    top: int = 5,
    cheaper_only: bool = False,
    any_position: bool = False,
    session: Session = Depends(get_session),
) -> list[schemas.SimilarPlayerOut]:
    player = session.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    vectors = build_player_vectors(session)
    if cheaper_only:
        results = find_cheaper_alternatives(vectors, player_id, k=top)
    else:
        results = find_similar_players(
            vectors, player_id, k=top, same_position_only=not any_position
        )
    return [schemas.SimilarPlayerOut.model_validate(r) for r in results]
