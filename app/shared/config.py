# app\shared\config.py
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
    APP_NAME: str = "Abstract Wiki Architect"
    
    # Alias 'ENV' to 'APP_ENV' so older code finding settings.ENV works
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT
    
    @property
    def ENV(self) -> str:
        """Alias for APP_ENV to support legacy calls (settings.ENV)."""
        return self.APP_ENV.value

    DEBUG: bool = True
    
    # --- Security ---
    # FIX: Default to None. This enables the "Dev Bypass" in dependencies.py.
    # If you want security, set API_SECRET in your .env file.
    API_SECRET: Optional[str] = None
    
    # --- Logging & Observability ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    OTEL_SERVICE_NAME: str = "architect-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # --- Messaging & State (Redis) ---
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_QUEUE_NAME: str = "architect_tasks"
    SESSION_TTL_SEC: int = 600  # Default 10 minutes

    # --- External Services ---
    WIKIDATA_SPARQL_URL: str = "https://query.wikidata.org/sparql"
    WIKIDATA_TIMEOUT: int = 30
    
    # --- AI & DevOps (v2.0) ---
    # Credentials for The Architect, Surgeon, and Judge agents
    # Ensure GEMINI_API_KEY is available
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_API_KEY: Optional[str] = None # Deprecated alias for Gemini
    AI_MODEL_NAME: str = "gemini-1.5-pro"
    
    # GitHub Integration
    GITHUB_TOKEN: Optional[str] = None
    REPO_URL: str = "https://github.com/your-org/abstract-wiki-architect"

    # --- Persistence ---
    STORAGE_BACKEND: StorageBackend = StorageBackend.FILESYSTEM
    
    # FILESYSTEM CONFIG
    # Default to current working directory if not set
    FILESYSTEM_REPO_PATH: str = os.getcwd()
    
    # S3 Config
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str = "abstract-wiki-grammars"

    # --- Worker Configuration ---
    WORKER_CONCURRENCY: int = 2

    # --- Feature Flags ---
    USE_MOCK_GRAMMAR: bool = False
    GF_LIB_PATH: str = "/usr/local/lib/gf"

    # --- Dynamic Path Resolution ---
    
    @property
    def TOPOLOGY_WEIGHTS_PATH(self) -> str:
        return os.path.join(self.FILESYSTEM_REPO_PATH, "data", "config", "topology_weights.json")

    @property
    def GOLD_STANDARD_PATH(self) -> str:
        return os.path.join(self.FILESYSTEM_REPO_PATH, "data", "tests", "gold_standard.json")

    @property
    def PGF_PATH(self) -> str:
        """
        Dynamically builds the path to the PGF binary.
        Prioritizes the AW_PGF_PATH env var if set, otherwise builds it from repo path.
        """
        # 1. Check direct override from Environment (Critical for Launch Script)
        env_override = os.getenv("AW_PGF_PATH")
        if env_override:
            return env_override

        # 2. Build from filesystem path
        base = self.FILESYSTEM_REPO_PATH.rstrip("/")
        filename = "AbstractWiki.pgf"
        
        # If the base path already points inside 'gf', don't append it again
        if base.endswith("gf"):
             return os.path.join(base, filename)
             
        return os.path.join(base, "gf", filename)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()