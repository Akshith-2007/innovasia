"""Application settings. Secrets come only from the backend environment / backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    data_gov_api_key: str = ""
    data_gov_base_url: str = "https://api.data.gov.in/resource"
    agmarknet_current_resource_id: str = "9ef84268-d588-465a-a308-a864a43d0070"
    agmarknet_history_resource_id: str = "35985678-0d79-46b4-9ed6-6f13308a1d24"
    crop_production_resource_id: str = "35be999b-0208-4354-b557-f6ca9a5355de"

    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    live_cache_ttl_seconds: int = 900
    http_timeout_seconds: float = 30.0
    page_size: int = 1000
    rate_limit_per_minute: int = 120  # per client IP; 0 disables
    # States kept when building market_prices.parquet (comma-separated; empty = all India). ADR-022.
    market_states: str = "Telangana,Andhra Pradesh,Karnataka"
    # Cold-storage admin portal and ESP32 device (ADR-024). Empty = feature disabled.
    admin_password: str = ""
    device_key: str = ""
    device_offline_after_seconds: int = 30

    data_dir: Path = BACKEND_DIR / "data"
    models_dir: Path = BACKEND_DIR / "models"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def metadata_dir(self) -> Path:
        return self.data_dir / "metadata"

    @property
    def market_prices_path(self) -> Path:
        return self.processed_dir / "market_prices.parquet"

    @property
    def crop_production_path(self) -> Path:
        return self.processed_dir / "crop_production.parquet"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def market_state_list(self) -> list[str] | None:
        states = [x.strip() for x in self.market_states.split(",") if x.strip()]
        return states or None

    @property
    def has_api_key(self) -> bool:
        return bool(self.data_gov_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
