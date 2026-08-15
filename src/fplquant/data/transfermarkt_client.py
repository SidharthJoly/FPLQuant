import datetime as dt
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from fplquant.config import settings


@dataclass(frozen=True)
class TransfermarktSearchResult:
    transfermarkt_id: int
    slug: str
    name: str
    club_name: str
    position: str


@dataclass(frozen=True)
class InjuryRecordData:
    season: str
    injury_type: str
    start_date: dt.date | None
    end_date: dt.date | None
    days_out: int | None
    games_missed: int | None


def _parse_date(value: str) -> dt.date | None:
    value = value.strip()
    if not value or value == "-":
        return None
    try:
        return dt.datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_days(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


class TransfermarktClient:
    """Scrapes Transfermarkt's public player search and injury-history pages.

    There is no official Transfermarkt API. This client identifies itself
    with a standard browser user agent (required — their servers reject
    generic scraper user agents) and callers are expected to rate-limit
    requests (see `fplquant.data.ingest_injuries`, which sleeps between calls).
    Intended for personal, non-commercial analytics use.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.transfermarkt_base_url
        self.session = requests.Session()
        self.session.headers["User-Agent"] = settings.transfermarkt_user_agent

    def _get_soup(self, path: str) -> BeautifulSoup:
        response = self.session.get(f"{self.base_url}{path}", timeout=settings.http_timeout_seconds)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def search_player(self, name: str) -> list[TransfermarktSearchResult]:
        soup = self._get_soup(f"/schnellsuche/ergebnis/schnellsuche?query={name}")
        return parse_search_results(soup)

    def get_injury_history(self, slug: str, transfermarkt_id: int) -> list[InjuryRecordData]:
        soup = self._get_soup(f"/{slug}/verletzungen/spieler/{transfermarkt_id}")
        return parse_injury_history(soup)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "TransfermarktClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()


def parse_search_results(soup: BeautifulSoup) -> list[TransfermarktSearchResult]:
    results: list[TransfermarktSearchResult] = []
    player_table = soup.find("table", class_="items")
    if player_table is None or not isinstance(player_table, Tag):
        return results

    for row in player_table.select("tbody > tr"):
        name_link = row.select_one("td.hauptlink a[href*='/profil/spieler/']")
        if name_link is None:
            continue
        href = name_link.get("href", "")
        match = re.search(r"/([\w-]+)/profil/spieler/(\d+)", str(href))
        if match is None:
            continue
        slug, tm_id = match.group(1), int(match.group(2))

        club_link = row.select_one("a[href*='/startseite/verein/']")
        position_cells = row.select("td.zentriert")

        results.append(
            TransfermarktSearchResult(
                transfermarkt_id=tm_id,
                slug=slug,
                name=name_link.get_text(strip=True),
                club_name=str(club_link.get("title", "")) if club_link else "",
                position=position_cells[0].get_text(strip=True) if position_cells else "",
            )
        )
    return results


def parse_injury_history(soup: BeautifulSoup) -> list[InjuryRecordData]:
    records: list[InjuryRecordData] = []
    injury_table = soup.find("table", class_="items")
    if injury_table is None or not isinstance(injury_table, Tag):
        return records

    for row in injury_table.select("tbody > tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 6:
            continue
        season = cells[0].get_text(strip=True)
        injury_type = cells[1].get_text(strip=True)
        start_date = _parse_date(cells[2].get_text(strip=True))
        end_date = _parse_date(cells[3].get_text(strip=True))
        days_out = _parse_days(cells[4].get_text(strip=True))
        games_missed_text = cells[5].get_text(strip=True)
        games_missed = int(games_missed_text) if games_missed_text.isdigit() else None

        records.append(
            InjuryRecordData(
                season=season,
                injury_type=injury_type,
                start_date=start_date,
                end_date=end_date,
                days_out=days_out,
                games_missed=games_missed,
            )
        )
    return records
