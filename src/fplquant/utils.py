from typing import Any


def as_float(value: Any) -> float:
    return float(value) if value not in (None, "") else 0.0
