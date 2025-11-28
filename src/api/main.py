"""
YACLib Enhanced - Main FastAPI Application

A modern replacement for YACReaderLibrary Server with enhanced features
while maintaining full backward compatibility with YACReader mobile apps.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from ..database import Database, get_default_db_path
from ..config import get_config
from .middleware import SessionMiddleware

# Load configuration
config = get_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.server.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting YACLib Enhanced Server...")
    logger.info(f"Configuration loaded: {len(config.libraries)} libraries defined")

    # Initialize database
    db_path = config.database.path or get_default_db_path()
    logger.info(f"Database: {db_path}")

    db = Database(db_path, echo=config.database.echo)
    # Note: Database schema initialization is handled by init_db.py script
    # which must be run before starting the server (see run_server.sh)

    # Store in app state
    app.state.db = db
    app.state.config = config

    # Initialize scheduler
    from ..services.scheduler import get_scheduler
    scheduler = get_scheduler(db)
    scheduler.load_schedules_from_db()
    app.state.scheduler = scheduler

    logger.info("YACLib Enhanced Server started successfully!")
    logger.info(f"Server running on {config.server.host}:{config.server.port}")

    yield

    # Shutdown
    logger.info("Shutting down YACLib Enhanced Server...")
    scheduler.shutdown()
    db.close()
    logger.info("Shutdown complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="YACLib Enhanced",
    description="Modern comic library server with YACReader compatibility",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# Session management middleware (YACReader compatibility)
app.add_middleware(SessionMiddleware, auto_create_session=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# Routes
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "service": "YACLib Enhanced",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/v1/info")
async def server_info():
    """Get server information"""
    db_path = get_default_db_path()

    return {
        "name": "YACLib Enhanced",
        "version": "1.0.0",
        "database": str(db_path),
        "features": {
            "legacy_api": True,
            "modern_api": True,
            "dual_thumbnails": True,
            "reading_progress": True,
            "series_detection": True,
            "collections": True,
        }
    }


# ============================================================================
# API Routers
# ============================================================================

from .routers import legacy_v1, scanners, libraries, user_interactions, config as config_router
from .routers import v2 as api_v2

# Legacy API v1 (YACReader compatible - plain text format)
app.include_router(legacy_v1.router, prefix="/library", tags=["Legacy API v1"])

# API v2 (YACReader compatible - JSON format) - mounted at /v2 for compatibility
app.include_router(api_v2.router, tags=["API v2"])

# Modern JSON API (Internal use)
app.include_router(libraries.router, prefix="/api/v1/libraries", tags=["Libraries"])

# Scanner API (Metadata scanning) - Part of v2 enhanced API
app.include_router(scanners.router, prefix="/v2", tags=["Scanners"])

# Modern API v2 (New features)
app.include_router(user_interactions.router, prefix="/api/v2", tags=["User Interactions"])
app.include_router(config_router.router, prefix="/api/v2", tags=["Configuration"])

# Note: Comics and reading endpoints are already included in the v2 router above
# (see src/api/routers/v2/__init__.py which aggregates comics.router and reading.router)


# ============================================================================
# Static Files (for web UI)
# ============================================================================

# TODO: Mount static files for web UI
# app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level
    )
