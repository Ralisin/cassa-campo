from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cassa Campo API"
    database_url: str = "sqlite:///./cassa_campo.sqlite3"
    jwt_secret: str = "development-only-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    cors_origins: str = "http://localhost:5173"
    supabase_url: str | None = None
    supabase_secret_key: str | None = None
    supabase_storage_bucket: str = "receipts"
    max_receipt_size_mb: int = 10
    system_admin_email: str = "massimo@admin.it"
    system_admin_name: str = "Massimo"
    system_admin_password: str = "CassaCampo2026!"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
