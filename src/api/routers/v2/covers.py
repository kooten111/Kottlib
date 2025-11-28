"""
API v2 Router - MangaDex Covers

Endpoints for fetching and selecting cover images from MangaDex,
independent of which metadata scanner was used.
"""

import logging
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ....database import (
    get_library_by_id,
    get_comic_by_id,
    get_covers_dir,
    create_cover,
)
from ....services.mangadex_client import get_mangadex_client, MangaDexCover

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class MangaDexCoverItem(BaseModel):
    """Single cover from MangaDex"""
    cover_id: str
    manga_id: str
    volume: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: str
    full_url: str


class MangaDexMangaResult(BaseModel):
    """Manga with covers from MangaDex search"""
    manga_id: str
    title: str
    alt_titles: List[str] = []
    description: Optional[str] = None
    year: Optional[int] = None
    status: Optional[str] = None
    covers: List[MangaDexCoverItem] = []


class MangaDexSearchResponse(BaseModel):
    """Response for MangaDex cover search"""
    comic_id: int
    comic_title: Optional[str]
    comic_series: Optional[str]
    search_query: str
    results: List[MangaDexMangaResult]


class FetchCoverRequest(BaseModel):
    """Request to fetch and set a MangaDex cover"""
    cover_id: str
    manga_id: str


class FetchCoverResponse(BaseModel):
    """Response after fetching a cover"""
    success: bool
    message: str
    cover_id: Optional[int] = None
    source_url: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/comic/{comic_id}/covers/mangadex")
async def search_mangadex_covers(
    comic_id: int,
    request: Request,
    query: Optional[str] = None
) -> MangaDexSearchResponse:
    """
    Search MangaDex for covers matching this comic's series/title

    If no query is provided, uses the comic's series name or title.

    Returns list of available covers with thumbnails for each matching manga.
    """
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Determine search query
        search_query = query
        if not search_query:
            # Prefer series name, fallback to title
            search_query = comic.series or comic.title or comic.filename

            # Clean up the query - remove file extension if using filename
            if search_query and search_query == comic.filename:
                search_query = Path(search_query).stem

        if not search_query:
            raise HTTPException(
                status_code=400,
                detail="No search query provided and comic has no title/series"
            )

        logger.info(f"Searching MangaDex covers for comic {comic_id} with query: {search_query}")

        # Search MangaDex
        client = get_mangadex_client()
        search_results = client.search_and_get_covers(
            search_query,
            limit_manga=5,
            limit_covers=20
        )

        # Convert to response format
        results = []
        for manga_data in search_results:
            covers = [
                MangaDexCoverItem(
                    cover_id=c['cover_id'],
                    manga_id=manga_data['manga_id'],
                    volume=c.get('volume'),
                    description=c.get('description'),
                    thumbnail_url=c['thumbnail_url'],
                    full_url=c['full_url']
                )
                for c in manga_data.get('covers', [])
            ]

            results.append(MangaDexMangaResult(
                manga_id=manga_data['manga_id'],
                title=manga_data['title'],
                alt_titles=manga_data.get('alt_titles', []),
                description=manga_data.get('description'),
                year=manga_data.get('year'),
                status=manga_data.get('status'),
                covers=covers
            ))

        return MangaDexSearchResponse(
            comic_id=comic_id,
            comic_title=comic.title,
            comic_series=comic.series,
            search_query=search_query,
            results=results
        )


@router.post("/comic/{comic_id}/covers/mangadex/fetch")
async def fetch_mangadex_cover(
    comic_id: int,
    request: Request,
    body: FetchCoverRequest
) -> FetchCoverResponse:
    """
    Download a selected MangaDex cover and set as comic's cover

    Downloads the cover image, generates thumbnails, and stores
    them in the library's covers directory.
    """
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        library = get_library_by_id(session, comic.library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        library_name = library.name

        logger.info(
            f"Fetching MangaDex cover for comic {comic_id}: "
            f"manga_id={body.manga_id}, cover_id={body.cover_id}"
        )

        # Get the cover info from MangaDex
        client = get_mangadex_client()
        covers = client.get_manga_covers(body.manga_id)

        # Find the requested cover
        target_cover: Optional[MangaDexCover] = None
        for cover in covers:
            if cover.cover_id == body.cover_id:
                target_cover = cover
                break

        if not target_cover:
            raise HTTPException(
                status_code=404,
                detail=f"Cover {body.cover_id} not found for manga {body.manga_id}"
            )

        # Download the cover image
        cover_image = client.download_cover_as_image(target_cover, use_thumbnail=False)
        if not cover_image:
            raise HTTPException(
                status_code=500,
                detail="Failed to download cover image from MangaDex"
            )

        # Generate thumbnails
        from ....scanner.thumbnail_generator import generate_dual_thumbnails

        covers_dir = get_covers_dir(library_name)
        custom_hash = f"{comic.hash}_mangadex"

        jpeg_ok, webp_ok = generate_dual_thumbnails(
            cover_image,
            covers_dir,
            custom_hash
        )

        if not jpeg_ok:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate cover thumbnails"
            )

        # Calculate paths for the generated thumbnails
        # Using hierarchical storage: covers/ab/abc123.jpg
        subdir = custom_hash[:2]
        jpeg_path = str(covers_dir / subdir / f"{custom_hash}.jpg")
        webp_path = str(covers_dir / subdir / f"{custom_hash}.webp") if webp_ok else None

        # Create cover record in database
        cover_record = create_cover(
            session,
            comic_id=comic_id,
            cover_type='custom',
            page_number=0,  # External cover, not from a page
            jpeg_path=jpeg_path,
            webp_path=webp_path,
            source='mangadex',
            source_url=target_cover.full_url
        )

        logger.info(
            f"Successfully set MangaDex cover for comic {comic_id}: "
            f"cover_id={cover_record.id}"
        )

        return FetchCoverResponse(
            success=True,
            message="Cover successfully fetched and set",
            cover_id=cover_record.id,
            source_url=target_cover.full_url
        )
