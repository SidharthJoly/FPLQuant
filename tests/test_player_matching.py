from fplquant.data.player_matching import match_player
from fplquant.data.transfermarkt_client import TransfermarktSearchResult


def test_matches_exact_name_and_club() -> None:
    candidates = [
        TransfermarktSearchResult(
            transfermarkt_id=433177,
            slug="bukayo-saka",
            name="Bukayo Saka",
            club_name="Arsenal FC",
            position="RW",
        ),
    ]
    result = match_player(
        fpl_full_name="Bukayo Saka",
        fpl_web_name="Saka",
        fpl_team_name="Arsenal",
        candidates=candidates,
    )
    assert result is not None
    assert result.transfermarkt_id == 433177


def test_prefers_club_matching_candidate_among_same_name() -> None:
    # Two players who could plausibly share a surname; club should disambiguate.
    candidates = [
        TransfermarktSearchResult(
            transfermarkt_id=1,
            slug="james-wrong-club",
            name="James Smith",
            club_name="Some Other FC",
            position="CB",
        ),
        TransfermarktSearchResult(
            transfermarkt_id=2,
            slug="james-right-club",
            name="James Smith",
            club_name="Arsenal FC",
            position="CB",
        ),
    ]
    result = match_player(
        fpl_full_name="James Smith",
        fpl_web_name="J.Smith",
        fpl_team_name="Arsenal",
        candidates=candidates,
    )
    assert result is not None
    assert result.transfermarkt_id == 2


def test_returns_none_when_no_candidates() -> None:
    result = match_player(
        fpl_full_name="Nobody Real", fpl_web_name="Nobody", fpl_team_name="Arsenal", candidates=[]
    )
    assert result is None


def test_returns_none_when_best_match_is_too_weak() -> None:
    candidates = [
        TransfermarktSearchResult(
            transfermarkt_id=1,
            slug="totally-different",
            name="Zzyzx Qwerty",
            club_name="Unrelated FC",
            position="GK",
        ),
    ]
    result = match_player(
        fpl_full_name="Bukayo Saka",
        fpl_web_name="Saka",
        fpl_team_name="Arsenal",
        candidates=candidates,
    )
    assert result is None


def test_matches_on_web_name_when_full_name_differs_more() -> None:
    # Transfermarkt sometimes lists a common nickname rather than the full name.
    candidates = [
        TransfermarktSearchResult(
            transfermarkt_id=9,
            slug="gakpo",
            name="Gakpo",
            club_name="Liverpool FC",
            position="LW",
        ),
    ]
    result = match_player(
        fpl_full_name="Cody Mathès Gakpo",
        fpl_web_name="Gakpo",
        fpl_team_name="Liverpool",
        candidates=candidates,
    )
    assert result is not None
    assert result.transfermarkt_id == 9
