from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FPLQUANT_", env_file=".env")

    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'fplquant.db'}"
    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    http_timeout_seconds: float = 15.0
    http_retries: int = 3

    transfermarkt_base_url: str = "https://www.transfermarkt.com"
    # Identify as a normal browser — Transfermarkt has no public API and blocks
    # generic scraper user agents. Requests are rate-limited (see
    # transfermarkt_request_delay_seconds) to stay polite to their servers.
    transfermarkt_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    transfermarkt_request_delay_seconds: float = 1.5


settings = Settings()
