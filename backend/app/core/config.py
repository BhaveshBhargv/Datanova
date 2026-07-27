"""Application configuration, driven entirely by environment variables."""
from functools import lru_cache

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    PROJECT_NAME: str = "AI Data Analytics Platform"
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = (
        "postgresql+psycopg2://analytics:analytics@localhost:5432/analytics"
    )

    # Auth / JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Field-level encryption (DB connection passwords). If unset, a key is
    # derived deterministically from SECRET_KEY (fine for dev; set explicitly
    # in production). Generate one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FIELD_ENCRYPTION_KEY: str | None = None

    # Data ingestion
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    IMPORT_ROW_CAP: int = 100_000

    # LLM (OpenRouter, OpenAI-compatible). If OPENROUTER_API_KEY is unset, AI
    # explanations fall back to a deterministic rule-based narrative.
    OPENROUTER_API_KEY: str | None = None
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    LLM_MAX_TOKENS: int = 500
    LLM_TIMEOUT: int = 30

    # AutoML
    AUTOML_MAX_ROWS: int = 20_000
    SHAP_SAMPLE: int = 300

    # CORS — comma-separated origins. Kept as a raw string because
    # pydantic-settings JSON-decodes list-typed env values before validators run.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_db_url(cls, v):
        """Render (and Heroku) hand out `postgres://` URLs; SQLAlchemy 2.x
        needs an explicit driver. Rewrite to `postgresql+psycopg2://`."""
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
