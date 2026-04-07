from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    openai_api_key: str
    database_url: str = "postgresql+asyncpg://churchill:0992717546@localhost:5432/churchill"
    redis_url: str = "redis://localhost:6379/0"
    openai_model: str = "gpt-4o-mini"
    daily_free_lessons: int = 1
    daily_pro_lessons: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
