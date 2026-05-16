import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    # LLM 모드
    LLM_MODE: str = "mock"  # "mock" | "vllm"

    # vLLM (LLM_MODE=vllm 일 때만 의미)
    VLLM_BASE_URL: str = "http://localhost:8002/v1"
    VLLM_MODEL: str = "gemma-4-31b-base"
    VLLM_API_KEY: str = "dummy"

    # 시스템 프롬프트 — 세 sLLM 별로 분리
    PERSONA_PROMPT_FILE: str = "prompts/persona_v1.txt"
    EXPLAIN_PROMPT_FILE: str = "prompts/explain_v1.txt"
    SUMMARY_PROMPT_FILE: str = "prompts/summary_v1.txt"

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
