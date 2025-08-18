from typing import List, Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="PROMETHEUS_"
    )
    # General settings
    version: str = "1.2"
    BASE_URL: str = f"/v{version}"
    PROJECT_NAME: str = "Prometheus"

    ENVIRONMENT: Literal["local", "production"]
    BACKEND_CORS_ORIGINS: List[str]
    ENABLE_AUTHENTICATION: bool

    # Logging
    LOGGING_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # Neo4j
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    NEO4J_BATCH_SIZE: int

    # Knowledge Graph
    WORKING_DIRECTORY: str
    KNOWLEDGE_GRAPH_MAX_AST_DEPTH: int
    KNOWLEDGE_GRAPH_CHUNK_SIZE: int
    KNOWLEDGE_GRAPH_CHUNK_OVERLAP: int
    MAX_TOKEN_PER_NEO4J_RESULT: int

    # LLM models
    ADVANCED_MODEL: str
    BASE_MODEL: str

    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_FORMAT_BASE_URL: Optional[str] = None
    OPENAI_FORMAT_API_KEY: Optional[str] = None

    # Model parameters
    ADVANCED_MODEL_MAX_INPUT_TOKENS: int
    ADVANCED_MODEL_TEMPERATURE: Optional[float] = None
    ADVANCED_MODEL_MAX_OUTPUT_TOKENS: Optional[int] = None

    BASE_MODEL_MAX_INPUT_TOKENS: int
    BASE_MODEL_TEMPERATURE: Optional[float] = None
    BASE_MODEL_MAX_OUTPUT_TOKENS: Optional[int] = None

    # Database
    DATABASE_URL: str

    # JWT Configuration
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_TIME: int = 7  # days


settings = Settings()
