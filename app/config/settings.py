from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["settings"]


class Settings(BaseSettings):
    """Application settings"""

    app_name: str = "TurboFox"

    debug: bool = True
    sqlite_database: str = ""

    # Monzo OAuth settings
    monzo_client_id: str = ""
    monzo_client_secret: str = ""
    monzo_redirect_uri: str = ""

    # Resend (transactional emails)
    resend_api_key: str = ""

    # Logfire
    logfire_environment: str = ""
    logfire_token: str = ""

    # Authentication
    session_cookie_name: str = "turbofox.session_id"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# Create settings instance to be imported by other modules
settings = Settings()
