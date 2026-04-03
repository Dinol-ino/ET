import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "ai-sales-agent")
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_sales"
    )
    hubspot_api_key: str = os.getenv("HUBSPOT_API_KEY", "")
    hubspot_base_url: str = os.getenv("HUBSPOT_BASE_URL", "https://api.hubapi.com")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_site_url: str = os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000")
    openrouter_app_name: str = os.getenv("OPENROUTER_APP_NAME", "ai-sales-agent")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))

    # Compatibility aliases for any remaining uppercase references.
    @property
    def APP_NAME(self) -> str:  # noqa: N802
        return self.app_name

    @property
    def APP_ENV(self) -> str:  # noqa: N802
        return self.app_env

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return self.database_url

    @property
    def HUBSPOT_API_KEY(self) -> str:  # noqa: N802
        return self.hubspot_api_key

    @property
    def HUBSPOT_BASE_URL(self) -> str:  # noqa: N802
        return self.hubspot_base_url

    @property
    def OPENROUTER_BASE_URL(self) -> str:  # noqa: N802
        return self.openrouter_base_url

    @property
    def OPENROUTER_MODEL(self) -> str:  # noqa: N802
        return self.openrouter_model

    @property
    def OPENROUTER_API_KEY(self) -> str:  # noqa: N802
        return self.openrouter_api_key

    @property
    def OPENROUTER_SITE_URL(self) -> str:  # noqa: N802
        return self.openrouter_site_url

    @property
    def OPENROUTER_APP_NAME(self) -> str:  # noqa: N802
        return self.openrouter_app_name

    @property
    def REQUEST_TIMEOUT_SECONDS(self) -> int:  # noqa: N802
        return self.request_timeout_seconds


settings = Settings()
