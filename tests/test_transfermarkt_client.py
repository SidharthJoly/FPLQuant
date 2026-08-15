from pathlib import Path

from bs4 import BeautifulSoup

from fplquant.data.transfermarkt_client import parse_injury_history, parse_search_results

FIXTURES_DIR = Path(__file__).parent / "data" / "transfermarkt"


def _soup(filename: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES_DIR / filename).read_text(), "lxml")


def test_parse_search_results_extracts_player() -> None:
    results = parse_search_results(_soup("search_bukayo_saka.html"))

    assert len(results) >= 1
    saka = results[0]
    assert saka.transfermarkt_id == 433177
    assert saka.slug == "bukayo-saka"
    assert saka.name == "Bukayo Saka"
    assert saka.club_name == "Arsenal FC"
    assert saka.position == "RW"


def test_parse_search_results_on_empty_page_returns_empty_list() -> None:
    soup = BeautifulSoup("<html><body>no results</body></html>", "lxml")
    assert parse_search_results(soup) == []


def test_parse_injury_history_extracts_records() -> None:
    records = parse_injury_history(_soup("injuries_bukayo_saka.html"))

    assert len(records) == 13
    first = records[0]
    assert first.season == "25/26"
    assert first.injury_type == "Achilles tendon problems"
    assert first.start_date is not None and first.start_date.isoformat() == "2026-03-23"
    assert first.end_date is not None and first.end_date.isoformat() == "2026-04-20"
    assert first.days_out == 29
    assert first.games_missed == 7


def test_parse_injury_history_on_empty_page_returns_empty_list() -> None:
    soup = BeautifulSoup("<html><body>no results</body></html>", "lxml")
    assert parse_injury_history(soup) == []
