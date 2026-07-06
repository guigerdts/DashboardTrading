from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, populated from environment / .env file.

    All environment variables use the ``TIP_`` prefix.
    Example: ``TIP_DEBUG=true``, ``TIP_DB_PATH=data/tip.db``
    """

    app_name: str = "Trade Intelligence Platform"
    debug: bool = False
    db_path: str = "../data/tip.db"
    db_echo: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_prefix": "TIP_"}


settings = Settings()
