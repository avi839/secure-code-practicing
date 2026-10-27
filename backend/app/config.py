"""
Application configuration using Pydantic Settings.

Values are read from environment variables, then from the repository-root
``.env`` and ``backend/.env`` (paths computed from this file, so the working
directory does not matter).
"""

from pathlib import Path
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH = (BACKEND_DIR / "data" / "securereflex.db").as_posix()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SQL_ECHO: bool = False
    LOG_LEVEL: str = "INFO"

    # Database (SQLite by default; PostgreSQL via postgresql+asyncpg://...)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"

    # AI providers (blank values are treated as "not configured")
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # Provider model defaults (verify current model ids with each vendor)
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    GEMINI_MODEL: str = "gemini-1.5-flash"

    DEFAULT_AI_PROVIDER: str = "demo"
    AI_TIMEOUT_SECONDS: int = 60
    MAX_TOKENS: int = 4096

    # Demo mode
    DEMO_MODE: bool = False
    DEMO_LATENCY_MS: int = 350

    # Security scanners
    BANDIT_ENABLED: bool = True
    SCANNER_TIMEOUT_SECONDS: int = 30

    # Reflexion
    DEFAULT_REFLEXION_ROUNDS: int = 3

    # Limits
    MAX_CODE_CHARS: int = 50000
    MAX_TASK_CHARS: int = 5000

    # CORS (comma-separated list)
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )
    # Opt-in: allow CORS origin "null" (pages opened from file://, sandboxed iframes).
    # Off by default because sandboxed iframes on any website also send Origin: null.
    ALLOW_NULL_ORIGIN: bool = False

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", mode="before")
    @classmethod
    def _blank_key_is_none(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("DEFAULT_REFLEXION_ROUNDS", mode="after")
    @classmethod
    def _clamp_rounds(cls, value: int) -> int:
        return max(1, min(10, int(value)))

    @model_validator(mode="after")
    def _resolve_sqlite_path(self):
        url = self.DATABASE_URL
        if url.startswith("sqlite"):
            parsed = make_url(url)
            database = parsed.database
            if database and database != ":memory:":
                path = Path(database)
                if not path.is_absolute():
                    path = (BACKEND_DIR / path).resolve()
                path.parent.mkdir(parents=True, exist_ok=True)
                self.DATABASE_URL = parsed.set(database=path.as_posix()).render_as_string(
                    hide_password=False
                )
        return self

    @property
    def cors_origins(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if self.ALLOW_NULL_ORIGIN and "null" not in origins:
            origins.append("null")
        return origins

    @property
    def database_backend(self) -> str:
        backend = make_url(self.DATABASE_URL).get_backend_name()
        if backend.startswith("postgres"):
            return "postgresql"
        return backend

    @property
    def masked_database_url(self) -> str:
        return make_url(self.DATABASE_URL).render_as_string(hide_password=True)


# Global settings instance
settings = Settings()
