from dataclasses import dataclass, field

# FPL element_type codes.
GOALKEEPER = 1
DEFENDER = 2
MIDFIELDER = 3
FORWARD = 4

POSITION_NAMES = {
    GOALKEEPER: "GKP",
    DEFENDER: "DEF",
    MIDFIELDER: "MID",
    FORWARD: "FWD",
}


@dataclass(frozen=True)
class PlayerCandidate:
    """A player as seen by the optimizer: just the fields the ILP needs."""

    player_id: int
    web_name: str
    team_id: int
    team_short_name: str
    element_type: int
    now_cost: int  # tenths of a million
    predicted_points: float


@dataclass(frozen=True)
class SquadConstraints:
    budget: int = 1000  # £100.0m, in tenths of a million
    position_limits: dict[int, int] = field(
        default_factory=lambda: {GOALKEEPER: 2, DEFENDER: 5, MIDFIELDER: 5, FORWARD: 3}
    )
    max_per_club: int = 3

    @property
    def squad_size(self) -> int:
        return sum(self.position_limits.values())


@dataclass(frozen=True)
class OptimizedSquad:
    players: list[PlayerCandidate]
    total_cost: int
    total_predicted_points: float


class InfeasibleSquadError(RuntimeError):
    """Raised when no squad satisfies the given constraints (e.g. budget too low)."""
