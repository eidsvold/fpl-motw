import os
from typing import List


class Settings:
    """Application settings with environment variable support."""

    # Server settings
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # CORS settings
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    # Static files
    STATIC_DIR: str = os.getenv("STATIC_DIR", "static")

    # Integrations
    FPL_API_BASE_URL: str = os.getenv(
        "FPL_API_BASE_URL", "https://fantasy.premierleague.com/api"
    )

    @property
    def is_production(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


settings = Settings()
