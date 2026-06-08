from pydantic_settings import BaseSettings


class Settings(BaseSettings):
#    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_clone"
    database_url: str = "sqlite+aiosqlite:///./telegram_clone.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "your-secret-key-change-in-production-abc123xyz"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    deepseek_api_key: str = ""
    deepseek_api_url: str = "https://api.deepseek.com/v1"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
