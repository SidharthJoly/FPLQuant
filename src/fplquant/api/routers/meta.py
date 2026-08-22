import datetime as dt

from fastapi import APIRouter

from fplquant.api import schemas
from fplquant.data.fpl_client import FPLClient

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/next-deadline", response_model=schemas.NextDeadlineOut)
def next_deadline() -> schemas.NextDeadlineOut:
    """The next gameweek's transfer deadline, straight from FPL's own
    bootstrap-static events — used for the header countdown clock.

    Filters on the deadline itself rather than the `finished` flag: FPL
    doesn't flip `finished` until a gameweek's matches are fully played out
    and bonus points are confirmed, which can lag the actual deadline by a
    day or more. During that lag the old "first unfinished event" pick
    would still be the gameweek whose deadline had already passed.
    """
    with FPLClient() as client:
        bootstrap = client.get_bootstrap_static()

    now = dt.datetime.now(dt.UTC)
    upcoming = []
    for event in bootstrap["events"]:
        deadline_time = event.get("deadline_time")
        if not deadline_time:
            continue
        deadline_dt = dt.datetime.fromisoformat(deadline_time.replace("Z", "+00:00"))
        if deadline_dt > now:
            upcoming.append(event)
    if not upcoming:
        return schemas.NextDeadlineOut(deadline=None, gameweek=None)

    next_event = min(upcoming, key=lambda event: event["deadline_time"])
    return schemas.NextDeadlineOut(deadline=next_event["deadline_time"], gameweek=next_event["id"])
