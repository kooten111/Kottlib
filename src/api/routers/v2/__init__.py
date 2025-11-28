"""
API v2 Router - Main Module

Aggregates all v2 API routers into a single router.
This modular structure replaces the monolithic api_v2.py file.
"""

from fastapi import APIRouter

# Import all sub-routers
from . import libraries
from . import folders
from . import comics
from . import reading
from . import search
from . import collections
from . import series
from . import session
from . import admin
from . import covers

# Create main v2 router with prefix
router = APIRouter(prefix="/v2")

# Include all sub-routers
router.include_router(libraries.router, tags=["v2-libraries"])
router.include_router(folders.router, tags=["v2-folders"])
router.include_router(comics.router, tags=["v2-comics"])
router.include_router(reading.router, tags=["v2-reading"])
router.include_router(search.router, tags=["v2-search"])
router.include_router(collections.router, tags=["v2-collections"])
router.include_router(series.router, tags=["v2-series"])
router.include_router(session.router, tags=["v2-session"])
router.include_router(admin.router, tags=["v2-admin"])
router.include_router(covers.router, tags=["v2-covers"])

# Export the main router
__all__ = ["router"]
