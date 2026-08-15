from sqlalchemy.orm import Session

from fplquant.form.scoring import _zscores, compute_form_scores
from fplquant.models.orm import Player, PlayerGameweekStat, Team


def _make_player(
    session: Session, *, fpl_id: int, web_name: str, team: Team, points: list[int]
) -> Player:
    player = Player(
        fpl_id=fpl_id,
        team_id=team.id,
        first_name=web_name,
        second_name=web_name,
        web_name=web_name,
        element_type=3,
        now_cost=60,
        selected_by_percent=10.0,
        form=0.0,
        total_points=sum(points),
        status="a",
    )
    session.add(player)
    session.flush()
    for round_number, pts in enumerate(points, start=1):
        session.add(
            PlayerGameweekStat(
                player_id=player.id,
                round=round_number,
                minutes=90,
                total_points=pts,
                ict_index=float(pts),  # keep it simple: underlying tracks points 1:1
            )
        )
    session.flush()
    return player


def test_zscores_of_identical_values_are_zero() -> None:
    assert _zscores([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]


def test_zscores_single_value_is_zero() -> None:
    assert _zscores([5.0]) == [0.0]


def test_compute_form_scores_ranks_in_form_player_first(db_session: Session) -> None:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    db_session.add(team)
    db_session.flush()

    _make_player(db_session, fpl_id=1, web_name="Hot", team=team, points=[2, 4, 8, 12])
    _make_player(db_session, fpl_id=2, web_name="Cold", team=team, points=[12, 8, 4, 2])
    db_session.flush()

    scores = compute_form_scores(db_session, halflife=2.0)

    assert [s.web_name for s in scores] == ["Hot", "Cold"]
    assert scores[0].combined_score > scores[1].combined_score


def test_compute_form_scores_respects_min_matches(db_session: Session) -> None:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    db_session.add(team)
    db_session.flush()

    _make_player(db_session, fpl_id=1, web_name="Established", team=team, points=[5, 5, 5])
    _make_player(db_session, fpl_id=2, web_name="OneGame", team=team, points=[10])
    db_session.flush()

    scores = compute_form_scores(db_session, min_matches=2)

    assert [s.web_name for s in scores] == ["Established"]


def test_matches_considered_reflects_history_length(db_session: Session) -> None:
    team = Team(fpl_id=1, name="Arsenal", short_name="ARS")
    db_session.add(team)
    db_session.flush()

    _make_player(db_session, fpl_id=1, web_name="Player", team=team, points=[1, 2, 3, 4, 5])
    db_session.flush()

    scores = compute_form_scores(db_session)

    assert scores[0].matches_considered == 5
