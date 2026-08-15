from difflib import SequenceMatcher

from fplquant.data.transfermarkt_client import TransfermarktSearchResult
from fplquant.utils import normalize_text

NAME_MATCH_THRESHOLD = 0.6
CLUB_MATCH_BONUS = 0.25


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def match_player(
    *,
    fpl_full_name: str,
    fpl_web_name: str,
    fpl_team_name: str,
    candidates: list[TransfermarktSearchResult],
) -> TransfermarktSearchResult | None:
    """Pick the best Transfermarkt search result for an FPL player.

    Scores each candidate on name similarity (against both the player's full
    name and their FPL "web name", since Transfermarkt sometimes lists a
    nickname), with a bonus when the candidate's club also matches the
    player's current FPL team. Returns None if the best score doesn't clear
    `NAME_MATCH_THRESHOLD` — ambiguous or missing matches are skipped rather
    than guessed at, since a wrong match would silently poison injury data.
    """
    best_candidate: TransfermarktSearchResult | None = None
    best_score = 0.0

    for candidate in candidates:
        name_score = max(
            _name_similarity(fpl_full_name, candidate.name),
            _name_similarity(fpl_web_name, candidate.name),
        )
        club_score = _name_similarity(fpl_team_name, candidate.club_name)
        score = name_score + (CLUB_MATCH_BONUS if club_score > 0.5 else 0.0)

        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate is None or best_score < NAME_MATCH_THRESHOLD:
        return None
    return best_candidate
