from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    DATABASE_URL: str
    # comma separated list of origins or '*' for all
    CORS_ORIGINS: Optional[str] = "*"

    class Config:
        env_file = ".env"


settings = Settings()
