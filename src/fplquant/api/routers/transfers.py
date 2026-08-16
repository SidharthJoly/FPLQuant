from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fplquant.api import schemas
from fplquant.api.deps import get_session
from fplquant.data.fpl_client import FPLClient
from fplquant.optimizer.candidates import (
    build_candidates_from_db,
    build_risk_adjusted_candidates_from_db,
)
from fplquant.transfers.planner import propose_transfers
from fplquant.transfers.team_lookup import TeamNotFoundError, fetch_current_squad

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("/plan", response_model=schemas.TransferPlanResponse)
def plan_transfers(
    request: schemas.TransferPlanRequest, session: Session = Depends(get_session)
) -> schemas.TransferPlanResponse:
    """Pull a manager's current squad from their public FPL team ID and
    recommend the transfers (if any) worth making this gameweek.
    """
    with FPLClient() as client:
        try:
            current_team = fetch_current_squad(client, session, request.fpl_team_id)
        except TeamNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if request.risk_adjusted:
        candidates = build_risk_adjusted_candidates_from_db(
            session, risk_aversion=request.risk_aversion, injury_weight=request.injury_weight
        )
    else:
        candidates = build_candidates_from_db(session)

    plan = propose_transfers(
        current_team.squad,
        candidates,
        bank=current_team.bank,
        free_transfers=request.free_transfers,
        max_per_club=request.max_per_club,
        chip=request.chip,
    )

    return schemas.TransferPlanResponse(
        team_name=current_team.team_name,
        event_id=current_team.event_id,
        bank=current_team.bank,
        chip=plan.chip,
        current_squad=[schemas.SquadPlayerOut.model_validate(p) for p in current_team.squad],
        transfers=[
            schemas.TransferPairOut(
                out=schemas.SquadPlayerOut.model_validate(pair.out),
                player_in=schemas.SquadPlayerOut.model_validate(pair.in_),
            )
            for pair in plan.transfers
        ],
        transfers_made=plan.transfers_made,
        free_transfers=plan.free_transfers,
        hit_cost=plan.hit_cost,
        points_gain_before_hit=plan.points_gain_before_hit,
        points_gain_after_hit=plan.points_gain_after_hit,
        worth_it=plan.worth_it,
        resulting_squad=[
            schemas.SquadPlayerOut.model_validate(p) for p in plan.resulting_squad.players
        ],
        starting_xi=schemas.StartingXIOut(
            formation=plan.starting_xi.formation,
            starters=[schemas.SquadPlayerOut.model_validate(p) for p in plan.starting_xi.starters],
            bench=[schemas.SquadPlayerOut.model_validate(p) for p in plan.starting_xi.bench],
            captain=schemas.SquadPlayerOut.model_validate(plan.starting_xi.captain),
            vice_captain=schemas.SquadPlayerOut.model_validate(plan.starting_xi.vice_captain),
            starting_predicted_points=plan.starting_xi.starting_predicted_points,
            bench_boost_value=plan.starting_xi.bench_boost_value,
            triple_captain_value=plan.starting_xi.triple_captain_value,
        ),
    )
