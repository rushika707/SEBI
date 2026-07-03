import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SEBI CoPilot API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Auth Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "sebi_copilot_super_secret_key_change_me_in_prod")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sebi_copilot.db")
    
    # Queue / Broker
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Vector DB
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    
    # Graph DB
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    
    # LLM Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Fallback Toggle
    # If True, checks db connection and automatically switches to sqlite/in-memory if primary is down
    AUTO_FALLBACK: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
