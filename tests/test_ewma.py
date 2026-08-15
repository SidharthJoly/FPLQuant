import pytest

from fplquant.form.ewma import ewma


def test_empty_sequence_returns_zero() -> None:
    assert ewma([], halflife=3.0) == 0.0


def test_constant_series_returns_that_constant() -> None:
    assert ewma([5.0, 5.0, 5.0, 5.0], halflife=2.0) == pytest.approx(5.0)


def test_single_value_returns_that_value() -> None:
    assert ewma([7.0], halflife=3.0) == pytest.approx(7.0)


def test_recent_values_weighted_more_heavily() -> None:
    rising = ewma([0.0, 0.0, 0.0, 10.0], halflife=1.0)
    falling = ewma([10.0, 0.0, 0.0, 0.0], halflife=1.0)
    assert rising > falling


def test_short_halflife_tracks_latest_value_closely() -> None:
    result = ewma([0.0, 0.0, 0.0, 10.0], halflife=0.1)
    assert result == pytest.approx(10.0, abs=0.5)


def test_long_halflife_approaches_simple_average() -> None:
    values = [2.0, 4.0, 6.0, 8.0]
    result = ewma(values, halflife=1000.0)
    assert result == pytest.approx(sum(values) / len(values), abs=0.05)


def test_nonpositive_halflife_raises() -> None:
    with pytest.raises(ValueError):
        ewma([1.0, 2.0], halflife=0.0)
