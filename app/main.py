# app/main.py
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# --- ARQ / Redis Imports ---
from arq import create_pool
from arq.connections import RedisSettings

from app.shared.config import settings, AppEnv
from app.shared.container import container  # <--- NEW: Import DI Container

# =========================================================================
# CRITICAL FIX: Force Security OFF
settings.API_SECRET = None 
# =========================================================================

from app.shared.telemetry import setup_telemetry, instrument_fastapi

# --- NEW: Import Specific Smart Routers (NOT 'routes') ---
from app.adapters.api.routers import generation, health, management

# Configure basic logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    if settings.LOG_FORMAT == "console"
    else '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application Lifecycle Manager."""
    # 1. Initialize OpenTelemetry
    setup_telemetry(settings.OTEL_SERVICE_NAME)
    
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")

    # --- NEW: Wire Dependency Injection ---
    container.wire(modules=[
        "app.adapters.api.routers.generation",
        "app.adapters.api.routers.management",
        "app.adapters.api.routers.health",
        "app.adapters.api.dependencies"
    ])
    logger.info("Dependency Injection container wired.")
    
    # 2. Initialize Redis Connection Pool
    try:
        app.state.redis = await create_pool(
            RedisSettings.from_dsn(settings.REDIS_URL),
            default_queue_name=settings.REDIS_QUEUE_NAME
        )
        logger.info(f"Redis pool created. Connected to queue: {settings.REDIS_QUEUE_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise e

    yield
    
    # 3. Shutdown & Cleanup
    logger.info("Shutting down application...")
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
        logger.info("Redis pool closed.")

def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    app = FastAPI(
        title="Abstract Wiki Architect",
        version="2.0.0",
        description="Distributed Natural Language Generation Platform (Hexagonal/GF)",
        docs_url="/docs" if settings.APP_ENV != AppEnv.PRODUCTION else None,
        redoc_url="/redoc" if settings.APP_ENV != AppEnv.PRODUCTION else None,
        lifespan=lifespan
    )

    # 2. CORS Configuration
    origins = ["*"] if settings.DEBUG else ["https://your-domain.com"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Auto-Instrument FastAPI
    instrument_fastapi(app)

    # 4. Global Exception Handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "code": exc.status_code, "message": exc.detail}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "code": 500, "message": "Internal Server Error" if not settings.DEBUG else str(exc)}
        )

    # 5. Mount Routes
    # --- NEW: Mount specific V1 routers ---
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(generation.router, prefix="/api/v1")
    app.include_router(management.router, prefix="/api/v1")

    return app

# Entry point for Uvicorn
app = create_app()