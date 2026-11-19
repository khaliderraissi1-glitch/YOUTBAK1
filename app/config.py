from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "YouTube Downloader API"
    environment: str = "production"
    public_base_url: str = ""
    allowed_origins: str = "*"
    cookies_file: str = ""
    request_timeout_seconds: int = 45
    max_video_seconds: int = 7200
    cache_ttl_seconds: int = 900
    rate_limit: str = "30/minute"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
