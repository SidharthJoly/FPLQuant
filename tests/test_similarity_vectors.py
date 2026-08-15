from sqlalchemy.orm import Session

from fplquant.models.orm import Player, PlayerGameweekStat, Team
from fplquant.similarity.vectors import FEATURES, build_player_vectors, compute_player_vector


def _team(session: Session) -> Team:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    session.add(team)
    session.flush()
    return team


def _player(session: Session, team: Team, fpl_id: int, web_name: str) -> Player:
    player = Player(
        fpl_id=fpl_id,
        team_id=team.id,
        first_name=web_name,
        second_name=web_name,
        web_name=web_name,
        element_type=4,
        now_cost=80,
        status="a",
    )
    session.add(player)
    session.flush()
    return player


def test_returns_none_with_zero_minutes(db_session: Session) -> None:
    team = _team(db_session)
    player = _player(db_session, team, 1, "Bench")
    db_session.add(PlayerGameweekStat(player_id=player.id, round=1, minutes=0, goals_scored=0))
    db_session.flush()

    assert compute_player_vector(player) is None


def test_computes_per_90_rate(db_session: Session) -> None:
    team = _team(db_session)
    player = _player(db_session, team, 1, "Striker")
    # 180 minutes total, 2 goals -> 1.0 goals per 90
    db_session.add(PlayerGameweekStat(player_id=player.id, round=1, minutes=90, goals_scored=1))
    db_session.add(PlayerGameweekStat(player_id=player.id, round=2, minutes=90, goals_scored=1))
    db_session.flush()

    vector = compute_player_vector(player)

    assert vector is not None
    assert vector.total_minutes == 180
    goals_index = FEATURES.index("goals_scored")
    assert vector.values[goals_index] == 1.0


def test_build_player_vectors_skips_players_with_no_minutes(db_session: Session) -> None:
    team = _team(db_session)
    has_minutes = _player(db_session, team, 1, "Played")
    no_minutes = _player(db_session, team, 2, "Unused")
    db_session.add(
        PlayerGameweekStat(player_id=has_minutes.id, round=1, minutes=90, goals_scored=1)
    )
    db_session.add(PlayerGameweekStat(player_id=no_minutes.id, round=1, minutes=0))
    db_session.flush()

    vectors = build_player_vectors(db_session)

    assert [v.web_name for v in vectors] == ["Played"]
