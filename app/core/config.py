from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application settings loaded from environment or .env file."""

    # Core security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ENV: str = "production"

    # Database
    DATABASE_URL: str

    # CORS
    CORS_ORIGINS: Optional[str] = "*"

    # AI configuration
    AI_PROVIDER: str = "ollama"
    AI_BASE_URL: Optional[str] = "http://127.0.0.1:11434"
    AI_MODEL: Optional[str] = "gemma:2b"
    AI_API_KEY: Optional[str] = None
    # Legacy compatibility (deprecated): falls back when AI_BASE_URL is not provided
    OLLAMA_BASE_URL: Optional[str] = None
    AI_RATE_LIMIT_WINDOW_SECONDS: int = 60
    AI_RATE_LIMIT_MAX_REQUESTS: int = 30
    AI_RATE_LIMIT_TTL_SECONDS: int = 300
    AI_REQUEST_TIMEOUT_SECONDS: int = 30
    AI_RETRY_ATTEMPTS: int = 2
    AI_RETRY_BACKOFF_SECONDS: float = 0.5

    # AI audit storage policy (PII is avoided by default)
    AI_AUDIT_STORE_INPUT: bool = False
    AI_AUDIT_INPUT_MAX_LENGTH: int = 512

    # Circuit breaker for Ollama
    AI_CB_FAILURE_THRESHOLD: int = 5
    AI_CB_COOLDOWN_SECONDS: int = 30
    AI_CB_HISTORY_MAX: int = 50

    # Optional admin override header/token (e.g., for circuit reset)
    ADMIN_OVERRIDE_TOKEN: Optional[str] = None

    # AI safety/logging knobs
    AI_LOGGING_LEVEL: str = "hash"  # none|hash|truncated|full
    AI_MAX_INPUT_CHARS: int = 50000
    AI_MAX_OUTPUT_CHARS: int = 20000
    AI_DISABLE_PROMPT_STORAGE: bool = True

    # Retention (days)
    RETENTION_DAYS_LOGS: int = 365
    RETENTION_DAYS_TOKENS: int = 30
    RETENTION_DAYS_DOCUMENTS: int = 365
    RETENTION_DAYS_RAG: int = 365

    class Config:
        env_file = ".env"


settings = Settings()
