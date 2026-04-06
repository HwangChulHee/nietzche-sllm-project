import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"

    # RunPod / vLLM
    RUNPOD_API_KEY: str = ""
    RUNPOD_ENDPOINT_ID: str = ""

    # Embedding
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24시간

    # 테스트 환경 여부
    TESTING: bool = False

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_llm_available(self) -> bool:
        """RunPod API 키가 설정되어 있으면 True."""
        return bool(self.RUNPOD_API_KEY and self.RUNPOD_ENDPOINT_ID)


settings = Settings()
