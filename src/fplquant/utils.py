import unicodedata
from typing import Any


def as_float(value: Any) -> float:
    return float(value) if value not in (None, "") else 0.0


def normalize_text(text: str) -> str:
    """Lowercase, accent-stripped form of `text`, for accent-insensitive
    matching (e.g. "gyokeres" should still find "Gyökeres")."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.lower().strip()
