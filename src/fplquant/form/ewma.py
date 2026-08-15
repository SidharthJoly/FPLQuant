from collections.abc import Sequence


def ewma(values: Sequence[float], halflife: float) -> float:
    """Exponentially weighted moving average, most recent value weighted heaviest.

    `values` must be in chronological order (oldest first). `halflife` is the
    number of steps back at which a value's weight has decayed to half.
    Returns 0.0 for an empty sequence.
    """
    if not values:
        return 0.0
    if halflife <= 0:
        raise ValueError("halflife must be positive")

    decay = 0.5 ** (1.0 / halflife)
    weighted_sum = 0.0
    weight_total = 0.0
    weight = 1.0
    # Walk backwards from the most recent value, so the most recent gets weight 1.0.
    for value in reversed(values):
        weighted_sum += weight * value
        weight_total += weight
        weight *= decay
    return weighted_sum / weight_total
