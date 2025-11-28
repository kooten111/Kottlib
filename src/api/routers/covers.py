"""
API Router - External Covers

Endpoints for fetching covers from external providers (MangaDex, AniList, etc.).
"""

import logging
from io import BytesIO
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image

from ...database import (
    get_library_by_id,
    get_comic_by_id,
    get_covers_dir,
    create_cover,
)
from ...covers import (
    get_cover_provider_manager,
    CoverOption,
    CoverProviderError,
    CoverProviderRateLimitError,
)
from ...scanner.thumbnail_generator import (
    generate_dual_thumbnails,
    get_thumbnail_path,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================


class CoverOptionResponse(BaseModel):
    """Response model for a single cover option."""

    id: str
    source: str
    thumbnail_url: str
    full_url: str
    description: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ProviderCoversResponse(BaseModel):
    """Response model for covers from a single provider."""

    provider: str
    covers: List[CoverOptionResponse]


class AllProvidersCoversResponse(BaseModel):
    """Response model for covers from all providers."""

    providers: Dict[str, List[CoverOptionResponse]]


class FetchCoverRequest(BaseModel):
    """Request model for fetching and setting a cover."""

    provider: str
    cover_id: str


class FetchCoverResponse(BaseModel):
    """Response model after fetching a cover."""

    success: bool
    message: str
    cover_type: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================


def _cover_option_to_response(cover: CoverOption) -> CoverOptionResponse:
    """Convert CoverOption to response model."""
    return CoverOptionResponse(
        id=cover.id,
        source=cover.source,
        thumbnail_url=cover.thumbnail_url,
        full_url=cover.full_url,
        description=cover.description,
        width=cover.width,
        height=cover.height,
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/covers/providers", response_model=List[str])
async def list_providers(request: Request):
    """
    List available cover providers.

    Returns a list of registered provider names (e.g., ['mangadex', 'anilist']).
    """
    manager = get_cover_provider_manager()
    providers = manager.get_available_providers()
    logger.debug(f"Available cover providers: {providers}")
    return providers


@router.get(
    "/comic/{comic_id}/covers/external",
    response_model=AllProvidersCoversResponse,
)
async def search_external_covers(
    comic_id: int,
    request: Request,
    provider: Optional[str] = Query(
        None, description="Provider name (searches all if omitted)"
    ),
):
    """
    Search for covers from external providers for a comic.

    Uses the comic's series name (or title) as the search query.
    If provider is specified, only searches that provider.
    Otherwise, searches all available providers.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get the comic to find its series name
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Use series name or title as search query
        query = comic.series or comic.title or comic.filename
        if not query:
            raise HTTPException(
                status_code=400,
                detail="Comic has no series name or title for searching",
            )

        logger.info(f"Searching external covers for comic {comic_id}: query='{query}'")

        manager = get_cover_provider_manager()

        try:
            if provider:
                # Search specific provider
                if provider not in manager.get_available_providers():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown provider: {provider}",
                    )
                covers = manager.search(provider, query)
                results = {
                    provider: [_cover_option_to_response(c) for c in covers]
                }
            else:
                # Search all providers
                all_covers = manager.search_all(query)
                results = {
                    prov: [_cover_option_to_response(c) for c in covers]
                    for prov, covers in all_covers.items()
                }

            return AllProvidersCoversResponse(providers=results)

        except CoverProviderRateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise HTTPException(status_code=429, detail=str(e))
        except CoverProviderError as e:
            logger.error(f"Cover provider error: {e}")
            raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/comic/{comic_id}/covers/external/{provider_name}",
    response_model=ProviderCoversResponse,
)
async def search_provider_covers(
    comic_id: int,
    provider_name: str,
    request: Request,
):
    """
    Search a specific provider for covers for a comic.

    Uses the comic's series name (or title) as the search query.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get the comic to find its series name
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Use series name or title as search query
        query = comic.series or comic.title or comic.filename
        if not query:
            raise HTTPException(
                status_code=400,
                detail="Comic has no series name or title for searching",
            )

        logger.info(
            f"Searching {provider_name} covers for comic {comic_id}: query='{query}'"
        )

        manager = get_cover_provider_manager()

        if provider_name not in manager.get_available_providers():
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {provider_name}",
            )

        try:
            covers = manager.search(provider_name, query)
            return ProviderCoversResponse(
                provider=provider_name,
                covers=[_cover_option_to_response(c) for c in covers],
            )

        except CoverProviderRateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise HTTPException(status_code=429, detail=str(e))
        except CoverProviderError as e:
            logger.error(f"Cover provider error: {e}")
            raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/comic/{comic_id}/covers/external/fetch",
    response_model=FetchCoverResponse,
)
async def fetch_external_cover(
    comic_id: int,
    fetch_request: FetchCoverRequest,
    request: Request,
):
    """
    Download and set a cover from an external provider.

    Downloads the cover image, generates thumbnails, and sets it as
    the comic's custom cover.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get the comic
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Get the library for covers directory
        library = get_library_by_id(session, comic.library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        logger.info(
            f"Fetching cover for comic {comic_id}: "
            f"provider={fetch_request.provider}, cover_id={fetch_request.cover_id}"
        )

        manager = get_cover_provider_manager()

        if fetch_request.provider not in manager.get_available_providers():
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {fetch_request.provider}",
            )

        try:
            # Download the cover image
            image_data = manager.download_cover(
                fetch_request.provider, fetch_request.cover_id
            )

            # Open the image
            image = Image.open(BytesIO(image_data))

            # Get covers directory
            covers_dir = get_covers_dir(library.name)

            # Generate dual thumbnails (JPEG + WebP)
            jpeg_success, webp_success = generate_dual_thumbnails(
                image, covers_dir, comic.hash
            )

            if not jpeg_success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate JPEG thumbnail",
                )

            # Get thumbnail paths
            jpeg_path = get_thumbnail_path(covers_dir, comic.hash, "JPEG")
            webp_path = (
                get_thumbnail_path(covers_dir, comic.hash, "WEBP")
                if webp_success
                else None
            )

            # Create/update cover record with 'custom' type and source info
            cover = create_cover(
                session=session,
                comic_id=comic.id,
                cover_type="custom",
                page_number=0,  # External covers don't have a page number
                jpeg_path=str(jpeg_path),
                webp_path=str(webp_path) if webp_path else None,
                source=fetch_request.provider,
                source_id=fetch_request.cover_id,
            )

            session.commit()

            logger.info(
                f"Successfully fetched and set cover for comic {comic_id} "
                f"from {fetch_request.provider}"
            )

            return FetchCoverResponse(
                success=True,
                message="Cover fetched and set successfully",
                cover_type="custom",
            )

        except CoverProviderRateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise HTTPException(status_code=429, detail=str(e))
        except CoverProviderError as e:
            logger.error(f"Cover provider error: {e}")
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            logger.error(f"Error fetching cover: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch cover: {str(e)}",
            )
