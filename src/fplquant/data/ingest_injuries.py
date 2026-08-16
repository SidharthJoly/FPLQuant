import logging
import time
import urllib.parse

from sqlalchemy.orm import Session

from fplquant.config import settings
from fplquant.data.player_matching import match_player
from fplquant.data.transfermarkt_client import TransfermarktClient
from fplquant.models.base import session_scope
from fplquant.models.orm import InjuryRecord, Player

logger = logging.getLogger(__name__)


def resolve_transfermarkt_id(session: Session, client: TransfermarktClient, player: Player) -> None:
    """Search Transfermarkt for `player` and cache the match (or the lack of one).

    No-op if already resolved (matched or previously confirmed unmatched) —
    call `resolve_transfermarkt_id` only for players whose
    `transfermarkt_lookup_status == "unresolved"` to avoid needless requests.
    """
    full_name = f"{player.first_name} {player.second_name}"
    query = urllib.parse.quote(full_name)
    candidates = client.search_player(query)
    match = match_player(
        fpl_full_name=full_name,
        fpl_web_name=player.web_name,
        fpl_team_name=player.team.name,
        candidates=candidates,
    )
    if match is None:
        player.transfermarkt_lookup_status = "unmatched"
        logger.info("No Transfermarkt match for %s (%s)", full_name, player.team.short_name)
        return
    player.transfermarkt_id = match.transfermarkt_id
    player.transfermarkt_slug = match.slug
    player.transfermarkt_lookup_status = "matched"
    session.flush()


def sync_injury_history(session: Session, client: TransfermarktClient, player: Player) -> None:
    """Replace `player`'s injury records with a fresh scrape from Transfermarkt."""
    if player.transfermarkt_id is None or player.transfermarkt_slug is None:
        return

    records = client.get_injury_history(player.transfermarkt_slug, player.transfermarkt_id)

    session.query(InjuryRecord).filter_by(player_id=player.id).delete()
    for record in records:
        session.add(
            InjuryRecord(
                player_id=player.id,
                season=record.season,
                injury_type=record.injury_type,
                start_date=record.start_date,
                end_date=record.end_date,
                days_out=record.days_out,
                games_missed=record.games_missed,
            )
        )
    session.flush()


def sync_nationality(session: Session, client: TransfermarktClient, player: Player) -> None:
    """Fetch and store `player`'s nationality from their Transfermarkt profile.

    Unlike injury history, nationality doesn't change, so this only needs to
    run once per player — callers should only call it for players where
    `nationality is None`, to avoid re-fetching a page for no reason.
    """
    if player.transfermarkt_id is None or player.transfermarkt_slug is None:
        return

    player.nationality = client.get_nationality(player.transfermarkt_slug, player.transfermarkt_id)
    session.flush()


def run_injury_ingest(
    client: TransfermarktClient | None = None,
    limit: int | None = None,
    delay_seconds: float | None = None,
) -> None:
    """Resolve Transfermarkt IDs for unresolved players, then sync injury history.

    Rate-limited (one request-pair per player, `delay_seconds` apart) to stay
    polite to Transfermarkt. Given the request volume for a full player pool,
    this is meant to run far less often than the main FPL ingest — see
    .github/workflows/ingest_injuries.yml (weekly, not daily).
    """
    owns_client = client is None
    client = client or TransfermarktClient()
    delay = (
        delay_seconds if delay_seconds is not None else settings.transfermarkt_request_delay_seconds
    )
    try:
        with session_scope() as session:
            players = session.query(Player).filter_by(transfermarkt_lookup_status="unresolved")
            if limit is not None:
                players = players.limit(limit)
            unresolved = players.all()

            for i, player in enumerate(unresolved, start=1):
                resolve_transfermarkt_id(session, client, player)
                time.sleep(delay)
                if i % 25 == 0 or i == len(unresolved):
                    logger.info("Resolved %d/%d players", i, len(unresolved))

        with session_scope() as session:
            matched = session.query(Player).filter_by(transfermarkt_lookup_status="matched").all()
            for i, player in enumerate(matched, start=1):
                sync_injury_history(session, client, player)
                time.sleep(delay)
                if i % 25 == 0 or i == len(matched):
                    logger.info("Synced injury history for %d/%d players", i, len(matched))

        with session_scope() as session:
            needs_nationality = (
                session.query(Player)
                .filter_by(transfermarkt_lookup_status="matched", nationality=None)
                .all()
            )
            for i, player in enumerate(needs_nationality, start=1):
                sync_nationality(session, client, player)
                time.sleep(delay)
                if i % 25 == 0 or i == len(needs_nationality):
                    logger.info("Fetched nationality for %d/%d players", i, len(needs_nationality))
    finally:
        if owns_client:
            client.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_injury_ingest()


if __name__ == "__main__":
    main()
