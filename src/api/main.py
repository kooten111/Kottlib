"""
Kottlib - Main FastAPI Application

A modern replacement for YACReader Server with enhanced features
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

import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Kottlib Server...")

    # Initialize database
    db_path = config.database.path or get_default_db_path()
    logger.info(f"Database: {db_path}")

    # Get database echo setting from database (will be loaded after DB connection)
    db = Database(db_path, echo=False)  # Default to False initially
    # Note: Database schema initialization is handled by init_db.py script
    # which must be run before starting the server (see run_server.sh)

    # Store in app state
    app.state.db = db
    app.state.config = config

    # Initialize database settings and migrate legacy config if needed
    from ..database import initialize_default_settings, get_setting
    from ..services.config_sync import ensure_config_file, migrate_legacy_config_to_db, get_sync_summary
    from ..config import get_config_path
    
    with db.get_session() as session:
        # Initialize default settings in database if not present
        initialize_default_settings(session)
        session.commit()
        logger.info("Database settings initialized")
        
        # Load database echo setting
        db_echo = get_setting(session, 'database.echo')
        if db_echo is not None:
            db.echo = db_echo
            
        # Ensure minimal config file exists
        config_path = get_config_path()
        if not config_path.exists():
            logger.info("Config file not found, creating minimal bootstrap config...")
            ensure_config_file(session, config)

    # Initialize scheduler (fast, starts background thread)
    from ..services.scheduler import get_scheduler
    scheduler = get_scheduler(db)
    app.state.scheduler = scheduler

    # Define background startup tasks to run without blocking server startup
    async def run_background_startup():
        logger.info("Running background startup tasks...")
        
        # 1. Migrate legacy config (might be slow)
        try:
            with db.get_session() as session:
                logger.info("Checking for legacy config libraries to migrate...")
                # Run in executor to avoid blocking event loop
                loop = asyncio.get_running_loop()
                stats = await loop.run_in_executor(None, migrate_legacy_config_to_db, session)
                
                if stats['created'] > 0 or stats['updated'] > 0:
                    summary = get_sync_summary(stats)
                    logger.info(summary)
                else:
                    logger.info("No legacy config libraries to migrate")
        except Exception as e:
            logger.error(f"Background config migration failed: {e}", exc_info=True)

        # 2. Load schedules (DB query)
        try:
             # Run in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, scheduler.load_schedules_from_db)
            logger.info("Scheduler schedules loaded")
        except Exception as e:
            logger.error(f"Failed to load scheduler schedules: {e}", exc_info=True)
            
        logger.info("Background startup tasks complete")

    # Start background tasks
    asyncio.create_task(run_background_startup())

    logger.info("Kottlib Server started successfully!")
    logger.info(f"Server running on {config.server.host}:{config.server.port}")

    yield

    # Shutdown
    logger.info("Shutting down Kottlib Server...")
    scheduler.shutdown()
    db.close()
    logger.info("Shutdown complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Kottlib",
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
        "service": "Kottlib",
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
        "name": "Kottlib",
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
