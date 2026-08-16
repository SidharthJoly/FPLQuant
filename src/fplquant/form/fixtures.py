import statistics
from dataclasses import dataclass

from sqlalchemy.orm import Session

from fplquant.form.scoring import predicted_points_by_player
from fplquant.models.orm import Fixture, Player, Team
from fplquant.optimizer.types import DEFENDER, GOALKEEPER

# Clamp the opponent-strength multiplier so a single very strong/weak opponent
# can't swing a player's expected points more than this — the FDR-style signal
# should nudge the ranking, not dominate it.
_MIN_MULTIPLIER = 0.7
_MAX_MULTIPLIER = 1.3


@dataclass(frozen=True)
class FixtureAdjustedScore:
    player_id: int
    web_name: str
    base_points: float  # the season-form estimate, before any fixture adjustment
    opponent_team_id: int | None
    opponent_short_name: str | None
    is_home: bool | None
    difficulty: int | None  # FPL's own 1 (easiest) - 5 (hardest) rating for this fixture
    fixture_multiplier: float | None  # our own continuous opponent-strength multiplier
    chance_of_playing: float  # 0.0-1.0
    adjusted_points: float  # base_points * fixture_multiplier * chance_of_playing


def get_next_fixture_by_team(session: Session) -> dict[int, Fixture]:
    """Each team's next unplayed fixture, keyed by team_id.

    Ordered by kickoff time so this is genuinely the *next* match, not just
    any upcoming one. Teams with no unplayed fixture scheduled yet (e.g. a
    blank gameweek before the next round is confirmed) are simply absent.
    """
    fixtures = (
        session.query(Fixture)
        .filter(Fixture.finished.is_(False), Fixture.kickoff_time.isnot(None))
        .order_by(Fixture.kickoff_time.asc())
        .all()
    )
    next_by_team: dict[int, Fixture] = {}
    for fixture in fixtures:
        for team_id in (fixture.team_h_id, fixture.team_a_id):
            next_by_team.setdefault(team_id, fixture)
    return next_by_team


def _league_average_strengths(teams: list[Team]) -> tuple[float, float]:
    """League-average attack and defence strength, blended across home/away.

    Computed from the pool itself rather than hardcoded, so this keeps
    working if FPL ever rescales their strength ratings.
    """
    attack_values = [t.strength_attack_home for t in teams] + [
        t.strength_attack_away for t in teams
    ]
    defence_values = [t.strength_defence_home for t in teams] + [
        t.strength_defence_away for t in teams
    ]
    avg_attack = statistics.fmean(attack_values) if attack_values else 1.0
    avg_defence = statistics.fmean(defence_values) if defence_values else 1.0
    return avg_attack, avg_defence


def _fixture_multiplier(
    element_type: int,
    opponent: Team,
    opponent_is_home: bool,
    league_avg_attack: float,
    league_avg_defence: float,
) -> float:
    """How much easier/harder this fixture is than average, for this position.

    Goalkeepers and defenders score heavily from clean sheets, so what
    matters to them is the opponent's *attack* strength. Midfielders and
    forwards score from goal involvements, so what matters to them is the
    opponent's *defence* strength. Either way, a stronger opponent in the
    relevant discipline means a smaller multiplier.
    """
    if element_type in (GOALKEEPER, DEFENDER):
        relevant = (
            opponent.strength_attack_home if opponent_is_home else opponent.strength_attack_away
        )
        league_avg = league_avg_attack
    else:
        relevant = (
            opponent.strength_defence_home if opponent_is_home else opponent.strength_defence_away
        )
        league_avg = league_avg_defence

    if relevant <= 0:
        return 1.0
    multiplier = league_avg / relevant
    return max(_MIN_MULTIPLIER, min(_MAX_MULTIPLIER, multiplier))


def chance_of_playing(player: Player) -> float:
    """Estimated probability `player` plays their next match, 0.0-1.0.

    FPL's own `chance_of_playing_next_round` is authoritative when set (it's
    how they surface manager press-conference news, e.g. 75/50/25/0). When
    it's absent, an "a" (available) status means fully expected to play;
    any other status (injured/suspended/unavailable/on loan) with no percent
    given is treated as not expected to play, matching FPL's own convention
    that those statuses default to no percentage only when the outlook is
    clear-cut.
    """
    if player.chance_of_playing_next_round is not None:
        return player.chance_of_playing_next_round / 100
    return 1.0 if player.status == "a" else 0.0


def compute_fixture_adjusted_scores(
    session: Session, halflife: float = 3.0
) -> list[FixtureAdjustedScore]:
    """Expected points for each player's next match specifically — folding in
    FPL's official fixture difficulty, our own continuous opponent-strength
    multiplier, home/away venue, and the chance the player actually plays.

    This is the "will this player have a good game against this opponent at
    this venue" signal, built on top of the season-form baseline from
    `fplquant.form.scoring.predicted_points_by_player`.
    """
    base_points = predicted_points_by_player(session, halflife)
    next_fixture_by_team = get_next_fixture_by_team(session)
    teams_by_id = {t.id: t for t in session.query(Team).all()}
    league_avg_attack, league_avg_defence = _league_average_strengths(list(teams_by_id.values()))

    scores = []
    for player in session.query(Player).all():
        base = base_points.get(player.id, 0.0)
        fixture = next_fixture_by_team.get(player.team_id)
        play_prob = chance_of_playing(player)

        if fixture is None:
            # No fixture data to adjust by (a genuine blank gameweek, or
            # fixtures just haven't been ingested yet) — degrade to the
            # unadjusted season-form estimate rather than zeroing out, same
            # philosophy as predicted_points_by_player falling back to
            # ep_next with no gameweek history: a fixture signal is never a
            # hard dependency for producing *some* estimate.
            scores.append(
                FixtureAdjustedScore(
                    player_id=player.id,
                    web_name=player.web_name,
                    base_points=base,
                    opponent_team_id=None,
                    opponent_short_name=None,
                    is_home=None,
                    difficulty=None,
                    fixture_multiplier=None,
                    chance_of_playing=play_prob,
                    adjusted_points=base * play_prob,
                )
            )
            continue

        is_home = fixture.team_h_id == player.team_id
        opponent_id = fixture.team_a_id if is_home else fixture.team_h_id
        opponent = teams_by_id.get(opponent_id)
        difficulty = fixture.team_h_difficulty if is_home else fixture.team_a_difficulty

        if opponent is None:
            multiplier = 1.0
        else:
            multiplier = _fixture_multiplier(
                player.element_type, opponent, not is_home, league_avg_attack, league_avg_defence
            )

        scores.append(
            FixtureAdjustedScore(
                player_id=player.id,
                web_name=player.web_name,
                base_points=base,
                opponent_team_id=opponent_id,
                opponent_short_name=opponent.short_name if opponent else None,
                is_home=is_home,
                difficulty=difficulty,
                fixture_multiplier=multiplier,
                chance_of_playing=play_prob,
                adjusted_points=base * multiplier * play_prob,
            )
        )
    return sorted(scores, key=lambda s: s.adjusted_points, reverse=True)
