import datetime as dt

from sqlalchemy.orm import Session

from fplquant.data.ingest_injuries import resolve_transfermarkt_id, sync_injury_history
from fplquant.data.transfermarkt_client import InjuryRecordData, TransfermarktSearchResult
from fplquant.models.orm import InjuryRecord, Player, Team


class StubTransfermarktClient:
    def __init__(
        self,
        search_results: list[TransfermarktSearchResult],
        injury_records: list[InjuryRecordData],
    ) -> None:
        self._search_results = search_results
        self._injury_records = injury_records
        self.search_calls: list[str] = []
        self.injury_calls: list[tuple[str, int]] = []

    def search_player(self, name: str) -> list[TransfermarktSearchResult]:
        self.search_calls.append(name)
        return self._search_results

    def get_injury_history(self, slug: str, transfermarkt_id: int) -> list[InjuryRecordData]:
        self.injury_calls.append((slug, transfermarkt_id))
        return self._injury_records


def _team_and_player(session: Session) -> Player:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    session.add(team)
    session.flush()
    player = Player(
        fpl_id=1,
        team_id=team.id,
        first_name="Bukayo",
        second_name="Saka",
        web_name="Saka",
        element_type=3,
        now_cost=95,
        status="a",
    )
    session.add(player)
    session.flush()
    return player


def test_resolve_transfermarkt_id_stores_match(db_session: Session) -> None:
    player = _team_and_player(db_session)
    client = StubTransfermarktClient(
        search_results=[
            TransfermarktSearchResult(
                transfermarkt_id=433177,
                slug="bukayo-saka",
                name="Bukayo Saka",
                club_name="Arsenal FC",
                position="RW",
            )
        ],
        injury_records=[],
    )

    resolve_transfermarkt_id(db_session, client, player)  # type: ignore[arg-type]

    assert player.transfermarkt_id == 433177
    assert player.transfermarkt_slug == "bukayo-saka"
    assert player.transfermarkt_lookup_status == "matched"


def test_resolve_transfermarkt_id_marks_unmatched_when_no_good_candidate(
    db_session: Session,
) -> None:
    player = _team_and_player(db_session)
    client = StubTransfermarktClient(
        search_results=[
            TransfermarktSearchResult(
                transfermarkt_id=1,
                slug="nobody-similar",
                name="Zzyzx Qwerty",
                club_name="Unrelated FC",
                position="GK",
            )
        ],
        injury_records=[],
    )

    resolve_transfermarkt_id(db_session, client, player)  # type: ignore[arg-type]

    assert player.transfermarkt_id is None
    assert player.transfermarkt_lookup_status == "unmatched"


def test_sync_injury_history_replaces_records(db_session: Session) -> None:
    player = _team_and_player(db_session)
    player.transfermarkt_id = 433177
    player.transfermarkt_slug = "bukayo-saka"
    db_session.flush()

    # Seed a stale record that should be wiped on sync.
    db_session.add(InjuryRecord(player_id=player.id, season="20/21", injury_type="Stale"))
    db_session.flush()

    client = StubTransfermarktClient(
        search_results=[],
        injury_records=[
            InjuryRecordData(
                season="25/26",
                injury_type="Hamstring injury",
                start_date=dt.date(2025, 8, 23),
                end_date=dt.date(2025, 9, 17),
                days_out=26,
                games_missed=5,
            )
        ],
    )

    sync_injury_history(db_session, client, player)  # type: ignore[arg-type]

    records = db_session.query(InjuryRecord).filter_by(player_id=player.id).all()
    assert len(records) == 1
    assert records[0].injury_type == "Hamstring injury"
    assert client.injury_calls == [("bukayo-saka", 433177)]


def test_sync_injury_history_noop_when_unresolved(db_session: Session) -> None:
    player = _team_and_player(db_session)
    client = StubTransfermarktClient(search_results=[], injury_records=[])

    sync_injury_history(db_session, client, player)  # type: ignore[arg-type]

    assert client.injury_calls == []
