"""
FastAPI Dependencies for Kottlib API

Provides reusable dependencies for common patterns like database sessions,
authentication, and request validation.
"""

from typing import Generator
from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import Database


def get_db(request: Request) -> Database:
    """
    Get the database instance from app state.

    This is used as a sub-dependency for get_db_session.
    """
    return request.app.state.db


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Eliminates the repetitive pattern of:
        db = request.app.state.db
        with db.get_session() as session:
            ...

    Usage in route handlers:
        @router.get("/example")
        async def example(session: Session = Depends(get_db_session)):
            # Use session directly
            library = get_library_by_id(session, library_id)

    Note: This creates a new session context for each request.
    The session is automatically committed on success and rolled back on error.
    """
    db = request.app.state.db
    with db.get_session() as session:
        yield session


def require_library(library_id: int, session: Session = Depends(get_db_session)):
    """
    Dependency that validates a library exists and returns it.

    Usage:
        @router.get("/library/{library_id}/comics")
        async def get_comics(library = Depends(require_library)):
            # library is guaranteed to exist
            return {"library_name": library.name}

    Raises:
        HTTPException: 404 if library not found
    """
    from ..database import get_library_by_id

    library = get_library_by_id(session, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    return library


def require_comic(comic_id: int, session: Session = Depends(get_db_session)):
    """
    Dependency that validates a comic exists and returns it.

    Usage:
        @router.get("/comic/{comic_id}")
        async def get_comic(comic = Depends(require_comic)):
            # comic is guaranteed to exist
            return {"title": comic.title}

    Raises:
        HTTPException: 404 if comic not found
    """
    from ..database import get_comic_by_id

    comic = get_comic_by_id(session, comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    return comic


class LibraryAndComic:
    """Container for library and comic pair from dependency injection."""
    def __init__(self, library, comic, session: Session):
        self.library = library
        self.comic = comic
        self.session = session


def require_library_and_comic(
    library_id: int,
    comic_id: int,
    session: Session = Depends(get_db_session)
) -> LibraryAndComic:
    """
    Dependency that validates both library and comic exist.

    This is a common pattern in comic endpoints that need both.

    Usage:
        @router.get("/library/{library_id}/comic/{comic_id}")
        async def get_comic(data: LibraryAndComic = Depends(require_library_and_comic)):
            library = data.library
            comic = data.comic
            session = data.session

    Raises:
        HTTPException: 404 if library or comic not found
    """
    from ..database import get_library_by_id, get_comic_by_id

    library = get_library_by_id(session, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    comic = get_comic_by_id(session, comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")

    return LibraryAndComic(library, comic, session)
