import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum
from typing import Optional

class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

class StorageBackend(str, Enum):
    FILESYSTEM = "filesystem"
    S3 = "s3"

class Settings(BaseSettings):
    """
    Central Configuration Registry.
    Strictly typed and validated via Pydantic.
    """
    
    # --- Application Meta ---
    APP_NAME: str = "abstract-wiki-architect"
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT
    DEBUG: bool = False
    
    # --- Security ---
    API_SECRET: str = "change-me-for-production" 
    
    # --- Logging & Observability ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    OTEL_SERVICE_NAME: str = "architect-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None 

    # --- Messaging (Redis) ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_QUEUE_NAME: str = "architect_tasks"

    @property
    def REDIS_URL(self) -> str:
        # Matches 'redis_broker.py' expectation
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- External Services ---
    WIKIDATA_SPARQL_URL: str = "https://query.wikidata.org/sparql"
    WIKIDATA_TIMEOUT: int = 30
    
    # --- Persistence ---
    STORAGE_BACKEND: StorageBackend = StorageBackend.FILESYSTEM
    
    # FILESYSTEM CONFIG
    # Default to Docker path (/app), fallback to local dev path if env var missing
    FILESYSTEM_REPO_PATH: str = "/app"
    
    # S3 Config
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str = "abstract-wiki-grammars"

    # --- Worker Configuration ---
    WORKER_CONCURRENCY: int = 2

    # --- Feature Flags ---
    USE_MOCK_GRAMMAR: bool = False 
    GF_LIB_PATH: str = "/usr/local/lib/gf" # Default to Docker/Linux path
    GOOGLE_API_KEY: Optional[str] = None

    @property
    def AW_PGF_PATH(self) -> str:
        """
        Dynamically builds the path to the PGF binary.
        Ensures consistency between Backend and Worker services.
        """
        # CRITICAL FIX: Smart detection of 'gf' folder to prevent 'gf/gf/'
        base = self.FILESYSTEM_REPO_PATH.rstrip("/")
        
        # The filename MUST match what build_orchestrator.py produces
        filename = "AbstractWiki.pgf" 
        
        # If the base path already points inside 'gf', don't append it again
        if base.endswith("gf"):
             return os.path.join(base, filename)
             
        return os.path.join(base, "gf", filename)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()