"""
YACLib Enhanced - Main FastAPI Application

A modern replacement for YACReaderLibrary Server with enhanced features
while maintaining full backward compatibility with YACReader mobile apps.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from ..database import Database, get_default_db_path
from ..config import get_config

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
    db.init_db()

    # Store in app state
    app.state.db = db
    app.state.config = config

    logger.info("YACLib Enhanced Server started successfully!")
    logger.info(f"Server running on {config.server.host}:{config.server.port}")

    yield

    # Shutdown
    logger.info("Shutting down YACLib Enhanced Server...")
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
# CORS Configuration
# ============================================================================

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

from .routers import legacy_v1, libraries

# Legacy API (YACReader compatible)
app.include_router(legacy_v1.router, prefix="/library", tags=["Legacy API v1"])

# Modern JSON API
app.include_router(libraries.router, prefix="/api/v1/libraries", tags=["Libraries"])

# TODO: Add more routers
# from .routers import comics, reading
# app.include_router(comics.router, prefix="/api/v1/comics", tags=["Comics"])
# app.include_router(reading.router, prefix="/api/v1/reading", tags=["Reading"])


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
