import datetime as dt

from sqlalchemy.orm import Session

from fplquant.models.orm import InjuryRecord, Player, PlayerGameweekStat, Team
from fplquant.risk.injury import (
    RiskWeights,
    compute_age,
    compute_injury_risk_scores,
)

AS_OF = dt.date(2026, 8, 15)


def _team(session: Session) -> Team:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    session.add(team)
    session.flush()
    return team


def _player(
    session: Session,
    team: Team,
    *,
    fpl_id: int,
    web_name: str,
    element_type: int = 3,
    birth_date: dt.date | None = None,
    status: str = "a",
    chance_of_playing_next_round: int | None = None,
) -> Player:
    player = Player(
        fpl_id=fpl_id,
        team_id=team.id,
        first_name=web_name,
        second_name=web_name,
        web_name=web_name,
        element_type=element_type,
        now_cost=60,
        status=status,
        birth_date=birth_date,
        chance_of_playing_next_round=chance_of_playing_next_round,
    )
    session.add(player)
    session.flush()
    return player


def test_compute_age() -> None:
    age = compute_age(dt.date(1996, 8, 15), AS_OF)
    assert age is not None
    assert 29.9 < age < 30.1


def test_compute_age_none_when_birth_date_missing() -> None:
    assert compute_age(None, AS_OF) is None


def test_currently_injured_player_scores_highest(db_session: Session) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="Injured", status="i")
    _player(db_session, team, fpl_id=2, web_name="Fit", status="a")

    scores = compute_injury_risk_scores(db_session, as_of=AS_OF)

    assert scores[0].web_name == "Injured"
    assert scores[0].status_component == 1.0
    assert scores[0].risk_pct > scores[1].risk_pct


def test_doubtful_player_uses_chance_of_playing(db_session: Session) -> None:
    team = _team(db_session)
    _player(
        db_session,
        team,
        fpl_id=1,
        web_name="Doubtful25",
        status="d",
        chance_of_playing_next_round=25,
    )
    _player(
        db_session,
        team,
        fpl_id=2,
        web_name="Doubtful75",
        status="d",
        chance_of_playing_next_round=75,
    )

    scores = {s.web_name: s for s in compute_injury_risk_scores(db_session, as_of=AS_OF)}

    assert scores["Doubtful25"].status_component > scores["Doubtful75"].status_component


def test_older_player_has_higher_age_component(db_session: Session) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="Young", birth_date=dt.date(2004, 1, 1))
    _player(db_session, team, fpl_id=2, web_name="Old", birth_date=dt.date(1988, 1, 1))

    scores = {s.web_name: s for s in compute_injury_risk_scores(db_session, as_of=AS_OF)}

    assert scores["Old"].age_component > scores["Young"].age_component


def test_injury_history_increases_history_component(db_session: Session) -> None:
    team = _team(db_session)
    injury_prone = _player(db_session, team, fpl_id=1, web_name="InjuryProne")
    _player(db_session, team, fpl_id=2, web_name="Clean")
    for i in range(4):
        db_session.add(
            InjuryRecord(
                player_id=injury_prone.id,
                season="25/26",
                injury_type="Hamstring injury",
                start_date=AS_OF - dt.timedelta(days=100 + i * 30),
                days_out=20,
            )
        )
    db_session.flush()

    scores = {s.web_name: s for s in compute_injury_risk_scores(db_session, as_of=AS_OF)}

    assert scores["InjuryProne"].history_component > scores["Clean"].history_component
    assert scores["Clean"].history_component == 0.0


def test_old_injuries_outside_lookback_window_are_ignored(db_session: Session) -> None:
    team = _team(db_session)
    player = _player(db_session, team, fpl_id=1, web_name="OldInjury")
    db_session.add(
        InjuryRecord(
            player_id=player.id,
            season="15/16",
            injury_type="Ancient injury",
            start_date=AS_OF - dt.timedelta(days=3650),
            days_out=100,
        )
    )
    db_session.flush()

    scores = compute_injury_risk_scores(db_session, as_of=AS_OF)

    assert scores[0].history_component == 0.0


def test_recent_heavy_minutes_increase_load_component(db_session: Session) -> None:
    team = _team(db_session)
    heavy = _player(db_session, team, fpl_id=1, web_name="Heavy")
    light = _player(db_session, team, fpl_id=2, web_name="Light")
    for round_number in range(1, 5):
        db_session.add(PlayerGameweekStat(player_id=heavy.id, round=round_number, minutes=90))
        db_session.add(PlayerGameweekStat(player_id=light.id, round=round_number, minutes=10))
    db_session.flush()

    scores = {s.web_name: s for s in compute_injury_risk_scores(db_session, as_of=AS_OF)}

    assert scores["Heavy"].load_component > scores["Light"].load_component


def test_custom_weights_are_respected(db_session: Session) -> None:
    team = _team(db_session)
    _player(db_session, team, fpl_id=1, web_name="Injured", status="i")

    all_status_weight = RiskWeights(age=0, position=0, history=0, load=0, status=1.0)
    scores = compute_injury_risk_scores(db_session, as_of=AS_OF, weights=all_status_weight)

    assert scores[0].risk_pct == 100.0


def test_risk_pct_is_clamped_to_100(db_session: Session) -> None:
    team = _team(db_session)
    _player(
        db_session,
        team,
        fpl_id=1,
        web_name="MaxRisk",
        status="i",
        birth_date=dt.date(1980, 1, 1),
    )

    heavy_weights = RiskWeights(age=1.0, position=1.0, history=1.0, load=1.0, status=1.0)
    scores = compute_injury_risk_scores(db_session, as_of=AS_OF, weights=heavy_weights)

    assert scores[0].risk_pct <= 100.0
