"""Service settings (pydantic-settings, env prefix ``FLEET_``)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when the service cannot start because of bad configuration."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLEET_", env_file=None, extra="ignore")

    api_key: SecretStr | None = None
    db_url: str = "sqlite:///./data/fleet.db"
    data_dir: Path = Path("./data")
    hermes_home: Path = Path.home() / ".hermes"
    hermes_bin: str = "hermes"
    hermes_timeout_s: float = 120.0
    secret_key: SecretStr | None = Field(
        default=None, description="Fernet key for service-generated secrets"
    )
    log_json: bool = True
    # OpenViking (stage 7+)
    ov_url: str | None = None
    ov_root_key: SecretStr | None = None
    ov_account: str = "team"
    ov_trust_env: bool = False
    ov_timeout_s: float = 30.0

    @field_validator("api_key")
    @classmethod
    def _non_empty(cls, v: SecretStr | None) -> SecretStr | None:
        if v is not None and not v.get_secret_value().strip():
            return None
        return v

    def require_api_key(self) -> str:
        if self.api_key is None:
            raise ConfigError(
                "FLEET_API_KEY is not set: refusing to start without an API key "
                "(set FLEET_API_KEY to a long random string)"
            )
        return self.api_key.get_secret_value()

    @property
    def skill_pool_dir(self) -> Path:
        return self.data_dir / "skill-pool"

    @property
    def skill_views_dir(self) -> Path:
        return self.data_dir / "skill-views"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
