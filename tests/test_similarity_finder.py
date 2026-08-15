import numpy as np

from fplquant.similarity.finder import find_cheaper_alternatives, find_similar_players
from fplquant.similarity.vectors import FEATURES, PlayerVector


def _vector(
    player_id: int, web_name: str, element_type: int, now_cost: int, **feature_overrides: float
) -> PlayerVector:
    values = np.zeros(len(FEATURES))
    for feature, value in feature_overrides.items():
        values[FEATURES.index(feature)] = value
    return PlayerVector(
        player_id=player_id,
        web_name=web_name,
        team_id=1,
        element_type=element_type,
        now_cost=now_cost,
        total_minutes=900,
        values=values,
    )


def test_returns_empty_when_target_not_found() -> None:
    vectors = [_vector(1, "A", 4, 80, goals_scored=1.0)]
    assert find_similar_players(vectors, target_player_id=999) == []


def test_finds_most_similar_player_by_style() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0, assists=0.1)
    close = _vector(2, "Close", 4, 60, goals_scored=0.9, assists=0.1)
    far = _vector(3, "Far", 4, 60, goals_scored=0.0, assists=1.0, threat=5.0)
    vectors = [target, close, far]

    results = find_similar_players(vectors, target_player_id=1, k=2)

    assert results[0].web_name == "Close"


def test_excludes_target_from_results() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0)
    vectors = [target, _vector(2, "Other", 4, 60, goals_scored=1.0)]

    results = find_similar_players(vectors, target_player_id=1)

    assert all(r.player_id != 1 for r in results)


def test_same_position_only_filters_other_positions() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0)
    same_position = _vector(2, "Fwd", 4, 60, goals_scored=1.0)
    other_position = _vector(3, "Def", 2, 60, goals_scored=1.0)
    vectors = [target, same_position, other_position]

    results = find_similar_players(vectors, target_player_id=1, same_position_only=True)

    assert [r.web_name for r in results] == ["Fwd"]


def test_any_position_includes_other_positions() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0)
    other_position = _vector(2, "Def", 2, 60, goals_scored=1.0)
    vectors = [target, other_position]

    results = find_similar_players(vectors, target_player_id=1, same_position_only=False)

    assert len(results) == 1


def test_cheaper_only_excludes_pricier_players() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0)
    cheaper = _vector(2, "Cheaper", 4, 60, goals_scored=1.0)
    pricier = _vector(3, "Pricier", 4, 150, goals_scored=1.0)
    vectors = [target, cheaper, pricier]

    results = find_similar_players(vectors, target_player_id=1, cheaper_only=True)

    assert [r.web_name for r in results] == ["Cheaper"]


def test_find_cheaper_alternatives_wraps_same_position_and_cheaper() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0)
    cheaper_same_position = _vector(2, "CheaperFwd", 4, 60, goals_scored=1.0)
    cheaper_other_position = _vector(3, "CheaperDef", 2, 60, goals_scored=1.0)
    pricier_same_position = _vector(4, "PricierFwd", 4, 150, goals_scored=1.0)
    vectors = [target, cheaper_same_position, cheaper_other_position, pricier_same_position]

    results = find_cheaper_alternatives(vectors, target_player_id=1)

    assert [r.web_name for r in results] == ["CheaperFwd"]


def test_top_k_limits_results() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0)
    others = [_vector(i, f"P{i}", 4, 60, goals_scored=1.0) for i in range(2, 10)]

    results = find_similar_players([target] + others, target_player_id=1, k=3)

    assert len(results) == 3


def test_empty_candidate_pool_returns_empty() -> None:
    target = _vector(1, "Target", 4, 100, goals_scored=1.0)
    assert find_similar_players([target], target_player_id=1) == []
