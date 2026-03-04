"""
Kottlib-native API router.

This namespace is reserved for the WebUI and other Kottlib-specific clients.
YACReader compatibility lives under the legacy root/v1 and /v2 namespaces.
"""

from fastapi import APIRouter

from . import libraries
from . import comics
from . import collections
from . import search
from . import reading
from ..scanners import router as scanners_router
from ..v2.admin import router as admin_router
from ..config import router as config_router

router = APIRouter()

router.include_router(libraries.router, tags=["api-libraries"])
router.include_router(comics.router, tags=["api-comics"])
router.include_router(collections.router, tags=["api-collections"])
router.include_router(search.router, tags=["api-search"])
router.include_router(reading.router, tags=["api-reading"])
router.include_router(scanners_router, tags=["api-scanners"])
router.include_router(admin_router, tags=["api-admin"])
router.include_router(config_router, tags=["api-config"])

__all__ = ["router"]
