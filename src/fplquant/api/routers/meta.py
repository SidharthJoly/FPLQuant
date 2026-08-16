from fastapi import APIRouter

from fplquant.api import schemas
from fplquant.data.fpl_client import FPLClient

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/next-deadline", response_model=schemas.NextDeadlineOut)
def next_deadline() -> schemas.NextDeadlineOut:
    """The next gameweek's transfer deadline, straight from FPL's own
    bootstrap-static events — used for the header countdown clock.
    """
    with FPLClient() as client:
        bootstrap = client.get_bootstrap_static()

    upcoming = [
        event
        for event in bootstrap["events"]
        if not event.get("finished") and event.get("deadline_time")
    ]
    if not upcoming:
        return schemas.NextDeadlineOut(deadline=None, gameweek=None)

    next_event = min(upcoming, key=lambda event: event["deadline_time"])
    return schemas.NextDeadlineOut(deadline=next_event["deadline_time"], gameweek=next_event["id"])
