import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    # LLM
    LLM_MODE: str = "mock"  # "mock" | "vllm"
    LLM_BASE_URL: str = "http://localhost:8001/v1"
    LLM_MODEL: str = "gemma-4-26b-a4b-nietzsche"
    LLM_API_KEY: str = "dummy"

    # 시스템 프롬프트
    SYSTEM_PROMPT_FILE: str = "prompts/nietzsche_v1.txt"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/nietzsche_dev"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # 테스트 환경 여부
    TESTING: bool = False

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
