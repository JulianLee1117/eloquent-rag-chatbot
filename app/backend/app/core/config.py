from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl
from typing import List

class Settings(BaseSettings):
    python_env: str = "dev"
    # SQLAlchemy URL w/ psycopg3 driver
    postgres_url: str
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    # auth
    jwt_secret: str = "replace_me"
    jwt_expire_min: int = 30

    # RAG-related (placeholders for later steps)
    pinecone_api_key: str | None = None
    pinecone_index: str | None = None
    pinecone_env: str | None = None
    pinecone_host: AnyUrl | None = None
    embedding_model: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None

    # Reranker (optional)
    rerank_model: str | None = None
    rerank_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",  # ignore unrelated env vars rather than erroring
    )

settings = Settings()