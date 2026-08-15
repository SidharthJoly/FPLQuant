from sqlalchemy.orm import Session

from fplquant.data import ingest
from fplquant.models.orm import Fixture, Player, PlayerGameweekStat, Team

from .data.fixtures import (
    ELEMENTS_PAYLOAD,
    FIXTURES_PAYLOAD,
    PLAYER_HISTORY_PAYLOAD,
    TEAMS_PAYLOAD,
)


def test_upsert_teams_creates_then_updates(db_session: Session) -> None:
    teams = ingest.upsert_teams(db_session, TEAMS_PAYLOAD)
    assert len(teams) == 2
    assert db_session.query(Team).count() == 2

    updated_payload = [{**TEAMS_PAYLOAD[0], "name": "Arsenal FC"}, TEAMS_PAYLOAD[1]]
    ingest.upsert_teams(db_session, updated_payload)
    assert db_session.query(Team).count() == 2  # no duplicates
    assert db_session.query(Team).filter_by(fpl_id=1).one().name == "Arsenal FC"


def test_upsert_players_links_to_team(db_session: Session) -> None:
    teams = ingest.upsert_teams(db_session, TEAMS_PAYLOAD)
    players = ingest.upsert_players(db_session, ELEMENTS_PAYLOAD, teams)

    assert db_session.query(Player).count() == 1
    player = players[101]
    assert player.web_name == "Raya"
    assert player.team.short_name == "ARS"
    assert player.selected_by_percent == 31.2


def test_upsert_fixtures(db_session: Session) -> None:
    teams = ingest.upsert_teams(db_session, TEAMS_PAYLOAD)
    ingest.upsert_fixtures(db_session, FIXTURES_PAYLOAD, teams)

    assert db_session.query(Fixture).count() == 1
    fixture = db_session.query(Fixture).one()
    assert fixture.team_h.short_name == "ARS"
    assert fixture.team_a.short_name == "CHE"
    assert fixture.event == 1


def test_upsert_player_gameweek_stats_is_idempotent(db_session: Session) -> None:
    teams = ingest.upsert_teams(db_session, TEAMS_PAYLOAD)
    players = ingest.upsert_players(db_session, ELEMENTS_PAYLOAD, teams)
    player = players[101]

    ingest.upsert_player_gameweek_stats(db_session, player, PLAYER_HISTORY_PAYLOAD)
    ingest.upsert_player_gameweek_stats(db_session, player, PLAYER_HISTORY_PAYLOAD)

    assert db_session.query(PlayerGameweekStat).count() == 1
    stat = db_session.query(PlayerGameweekStat).one()
    assert stat.total_points == 6
    assert stat.expected_goals_conceded == 0.8
