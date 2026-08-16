from pydantic import BaseModel, ConfigDict, Field, field_validator

from fplquant.optimizer.starting_xi import VALID_FORMATIONS

_VALID_FORMATION_STRINGS = {f"{d}-{m}-{f}" for d, m, f in VALID_FORMATIONS}


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fpl_id: int
    web_name: str
    full_name: str
    team_id: int
    team_short_name: str
    element_type: int
    now_cost: int
    status: str
    selected_by_percent: float
    form: float
    ep_next: float
    nationality: str | None = None
    photo_url: str | None = None


class FormScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    web_name: str
    matches_considered: int
    points_form: float
    underlying_form: float
    combined_score: float


class InjuryRiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    web_name: str
    age: float | None
    age_component: float
    position_component: float
    history_component: float
    load_component: float
    status_component: float
    risk_pct: float


class PlayerDetailOut(PlayerOut):
    form_score: FormScoreOut | None = None
    injury_risk: InjuryRiskOut | None = None


class PlayerGameweekStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    round: int
    total_points: int
    minutes: int
    value: int
    selected: int


class PriceMomentumOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    web_name: str
    gameweeks_considered: int
    price_change: int
    price_change_pct: float
    net_transfers: int
    ownership_change: int
    ownership_change_pct: float


class VolatilityScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    web_name: str
    gameweeks_considered: int
    points_mean: float
    points_stdev: float
    coefficient_of_variation: float | None


class TeammateCorrelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: int
    player_a_id: int
    player_a_web_name: str
    player_b_id: int
    player_b_web_name: str
    overlap_gameweeks: int
    correlation: float


class SimilarPlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    web_name: str
    team_id: int
    now_cost: int
    similarity: float


class SquadPlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    web_name: str
    team_id: int
    team_short_name: str
    element_type: int
    now_cost: int
    predicted_points: float


class OptimizeRequest(BaseModel):
    budget: float = Field(default=100.0, gt=0, description="Budget in millions, e.g. 100.0")
    max_per_club: int = Field(default=3, ge=1)
    risk_adjusted: bool = Field(
        default=False, description="Maximize risk-adjusted points instead of raw points"
    )
    risk_aversion: float = Field(default=1.0, ge=0, description="Only with risk_adjusted=true")
    injury_weight: float = Field(default=1.0, ge=0, description="Only with risk_adjusted=true")
    formation: str | None = Field(
        default=None,
        description=(
            "Force a specific starting XI formation, e.g. '3-4-3'. "
            "Omit to auto-select the highest-scoring formation."
        ),
    )

    @field_validator("formation")
    @classmethod
    def _validate_formation(cls, value: str | None) -> str | None:
        if value is not None and value not in _VALID_FORMATION_STRINGS:
            raise ValueError(f"formation must be one of {sorted(_VALID_FORMATION_STRINGS)}")
        return value


class StartingXIOut(BaseModel):
    formation: str
    starters: list[SquadPlayerOut]
    bench: list[SquadPlayerOut]
    captain: SquadPlayerOut
    vice_captain: SquadPlayerOut
    starting_predicted_points: float
    bench_boost_value: float
    triple_captain_value: float


class OptimizeResponse(BaseModel):
    total_cost: int
    total_predicted_points: float
    squad: list[SquadPlayerOut]
    starting_xi: StartingXIOut
