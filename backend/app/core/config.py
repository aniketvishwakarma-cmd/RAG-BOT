from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    CIC_WINDOW_DAYS,
    CI_WINDOW_DAYS,
    CONSUMER_PENALTY_PER_DAY,
    LAYER_PRIORITY,
    REGULATOR_PENALTY_PER_DAY,
    TOTAL_RESOLUTION_DAYS,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "CIBIL-RegBot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALGORITHM: str = "HS256"

    POSTGRES_URL: str = "sqlite:///./cibil_regbot.db"
    SQL_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"

    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_LLM_MODEL: str = "gpt-4o"
    COHERE_API_KEY: str = ""
    COHERE_RERANK_MODEL: str = "rerank-v3.5"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_LLM_MODEL: str = "claude-3-5-sonnet-latest"

    RETRIEVAL_TOP_K: int = 50
    RERANK_TOP_N: int = 8
    VECTOR_WEIGHT: float = 0.70
    BM25_WEIGHT: float = 0.30
    MIN_CONFIDENCE_THRESHOLD: float = 0.65
    HITL_CONFIDENCE_TRIGGER: float = 0.75

    LAYER_PRIORITY: Dict[str, int] = Field(default_factory=lambda: dict(LAYER_PRIORITY))

    CONSUMER_PENALTY_PER_DAY: int = CONSUMER_PENALTY_PER_DAY
    REGULATOR_PENALTY_PER_DAY: int = REGULATOR_PENALTY_PER_DAY
    CI_WINDOW_DAYS: int = CI_WINDOW_DAYS
    CIC_WINDOW_DAYS: int = CIC_WINDOW_DAYS
    TOTAL_RESOLUTION_DAYS: int = TOTAL_RESOLUTION_DAYS

    CHUNK_MIN_TOKENS: int = 150
    CHUNK_MAX_TOKENS: int = 400
    RATE_LIMIT_PER_MINUTE: int = 30
    CACHE_TTL_SECONDS: int = 3600
    BM25_INDEX_PATH: str = "data/bm25_index.json"
    UPLOAD_DIR: str = "data/uploads"
    SAMPLE_DATA_DIR: str = "data/sample"
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

