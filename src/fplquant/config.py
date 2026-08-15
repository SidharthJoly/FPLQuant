from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FPLQUANT_", env_file=".env")

    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'fplquant.db'}"
    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    http_timeout_seconds: float = 15.0
    http_retries: int = 3


settings = Settings()
