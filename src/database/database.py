"""
Database Access Layer

Provides database connection, initialization, and basic CRUD operations.
"""

import os
import time
import uuid
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base, Library, Folder, Comic, Cover, User, Session as DBSession, ReadingProgress
import logging

logger = logging.getLogger(__name__)

# Import series utilities
try:
    from ..utils.series_utils import get_series_name_from_comic
except ImportError:
    from utils.series_utils import get_series_name_from_comic


# ============================================================================
# Database Configuration
# ============================================================================

def get_default_db_path() -> Path:
    """
    Get the default database path based on platform

    Linux: ~/.local/share/yaclib/yaclib.db
    macOS: ~/Library/Application Support/YACLib/yaclib.db
    Windows: %APPDATA%/YACLib/yaclib.db
    """
    import platform

    system = platform.system()

    if system == 'Linux':
        base_dir = Path.home() / '.local' / 'share' / 'yaclib'
    elif system == 'Darwin':  # macOS
        base_dir = Path.home() / 'Library' / 'Application Support' / 'YACLib'
    elif system == 'Windows':
        base_dir = Path(os.environ.get('APPDATA', Path.home())) / 'YACLib'
    else:
        # Fallback
        base_dir = Path.home() / '.yaclib'

    # Create directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)

    return base_dir / 'yaclib.db'


def get_covers_dir() -> Path:
    """Get the covers directory (same location as database)"""
    db_path = get_default_db_path()
    covers_dir = db_path.parent / 'covers'
    covers_dir.mkdir(parents=True, exist_ok=True)
    return covers_dir


# ============================================================================
# Database Engine and Session
# ============================================================================

class Database:
    """Database connection manager"""

    def __init__(self, db_path: Optional[Path] = None, echo: bool = False):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file (None = default location)
            echo: If True, log all SQL statements
        """
        if db_path is None:
            db_path = get_default_db_path()

        self.db_path = Path(db_path)
        self.db_url = f"sqlite:///{self.db_path}"

        # Create engine
        # Use NullPool for SQLite in multi-threaded scenarios to avoid connection sharing issues
        # Each session gets its own connection that's immediately returned after use
        from sqlalchemy.pool import NullPool
        self.engine = create_engine(
            self.db_url,
            echo=echo,
            poolclass=NullPool,  # No connection pooling - each thread gets its own connection
            connect_args={
                "check_same_thread": False,
                "timeout": 30  # 30 second timeout for lock acquisition
            }
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False  # Prevent issues with accessing objects after commit in multi-threaded context
        )

        logger.info(f"Database initialized: {self.db_path}")

    def init_db(self):
        """Initialize database schema (create tables)"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database schema created")

        # Create default admin user if not exists
        with self.get_session() as session:
            admin = session.query(User).filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    password_hash='changeme',  # Should be hashed in production!
                    is_admin=True,
                    is_active=True,
                    created_at=int(time.time())
                )
                session.add(admin)
                session.commit()
                logger.info("Created default admin user")

    @contextmanager
    def get_session(self):
        """
        Get a database session (context manager)

        Usage:
            with db.get_session() as session:
                # Use session here
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Close database connection"""
        self.engine.dispose()


# ============================================================================
# Library Operations
# ============================================================================

def create_library(
    session: Session,
    name: str,
    path: str,
    settings: Optional[dict] = None
) -> Library:
    """Create a new library"""
    now = int(time.time())

    library = Library(
        uuid=str(uuid.uuid4()),
        name=name,
        path=str(Path(path).resolve()),
        created_at=now,
        updated_at=now,
        scan_status='pending',
        settings=settings or {}
    )

    session.add(library)
    session.flush()  # Flush to get the ID without committing

    logger.info(f"Created library: {name} at {path}")
    return library


def get_library_by_id(session: Session, library_id: int) -> Optional[Library]:
    """Get library by ID"""
    return session.query(Library).filter_by(id=library_id).first()


def get_library_by_path(session: Session, path: str) -> Optional[Library]:
    """Get library by filesystem path"""
    return session.query(Library).filter_by(path=str(Path(path).resolve())).first()


def get_all_libraries(session: Session) -> List[Library]:
    """Get all libraries"""
    return session.query(Library).all()


def update_library_scan_status(
    session: Session,
    library_id: int,
    status: str,
    timestamp: Optional[int] = None
):
    """Update library scan status"""
    library = get_library_by_id(session, library_id)
    if library:
        library.scan_status = status
        library.last_scan_at = timestamp or int(time.time())
        library.updated_at = int(time.time())
        session.flush()  # Flush changes without committing


def update_library_series_tree_cache(
    session: Session,
    library_id: int,
    tree_data: str
):
    """
    Update the pre-computed series tree cache for a library

    Args:
        session: Database session
        library_id: Library ID
        tree_data: JSON string containing the serialized tree structure
    """
    library = get_library_by_id(session, library_id)
    if library:
        library.cached_series_tree = tree_data
        library.tree_cache_updated_at = int(time.time())
        library.updated_at = int(time.time())
        session.flush()  # Flush changes without committing


# ============================================================================
# Comic Operations
# ============================================================================

def create_comic(
    session: Session,
    library_id: int,
    path: str,
    filename: str,
    file_hash: str,
    file_size: int,
    file_modified_at: int,
    format: str,
    num_pages: int,
    folder_id: Optional[int] = None,
    **metadata
) -> Comic:
    """Create a new comic entry"""
    now = int(time.time())

    # Get TOP-LEVEL folder name for series (not immediate parent!)
    # Top-level folder = first folder under library root
    # Example: "Jojo's Bizarre Adventure (Colorized)/Part 3/Volume 01.cbz"
    #   -> TOP-LEVEL = "Jojo's Bizarre Adventure (Colorized)"
    #   -> NOT "Part 3"
    top_level_folder_name = None
    if folder_id:
        # OPTIMIZED: Use a recursive CTE to find top-level folder in ONE query
        # Get the folder and walk up parent chain
        from sqlalchemy import text

        result = session.execute(
            text("""
                WITH RECURSIVE folder_path AS (
                    -- Start with the comic's folder
                    SELECT id, name, parent_id, 0 as depth
                    FROM folders
                    WHERE id = :folder_id

                    UNION ALL

                    -- Walk up to parent
                    SELECT f.id, f.name, f.parent_id, fp.depth + 1
                    FROM folders f
                    INNER JOIN folder_path fp ON f.id = fp.parent_id
                    WHERE f.name != '__ROOT__'
                )
                -- Get the top-most folder (highest depth, before __ROOT__)
                SELECT name
                FROM folder_path
                ORDER BY depth DESC
                LIMIT 1
            """),
            {"folder_id": folder_id}
        ).fetchone()

        if result:
            top_level_folder_name = result[0]

    # Create comic with metadata
    comic = Comic(
        library_id=library_id,
        folder_id=folder_id,
        path=str(Path(path).resolve()),
        filename=filename,
        hash=file_hash,
        file_size=file_size,
        file_modified_at=file_modified_at,
        format=format,
        num_pages=num_pages,
        created_at=now,
        updated_at=now,
        **metadata
    )

    # Auto-populate normalized_series_name for fast series grouping
    # Use top-level folder name (the actual series folder)
    comic.normalized_series_name = get_series_name_from_comic(comic, top_level_folder_name)

    session.add(comic)
    session.flush()  # Flush to get the ID without committing

    logger.debug(f"Created comic: {filename} (series: {comic.normalized_series_name})")
    return comic


def get_comic_by_id(session: Session, comic_id: int) -> Optional[Comic]:
    """Get comic by ID"""
    return session.query(Comic).filter_by(id=comic_id).first()


def get_comic_by_hash(session: Session, file_hash: str, library_id: Optional[int] = None) -> Optional[Comic]:
    """
    Get comic by file hash

    Args:
        session: Database session
        file_hash: File hash to search for
        library_id: Optional library ID to filter by (allows same file in different libraries)
    """
    query = session.query(Comic).filter_by(hash=file_hash)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.first()


def get_comic_by_path_and_mtime(
    session: Session,
    path: str,
    file_modified_at: int,
    library_id: Optional[int] = None
) -> Optional[Comic]:
    """
    Get comic by file path and modification time (fast check before hashing).

    This is used to quickly skip unchanged files during re-scans without
    calculating expensive file hashes.

    Args:
        session: Database session
        path: Full file path to search for
        file_modified_at: File modification timestamp (Unix timestamp)
        library_id: Optional library ID to filter by

    Returns:
        Comic if found with matching path and mtime, None otherwise
    """
    query = session.query(Comic).filter_by(path=path, file_modified_at=file_modified_at)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.first()


def get_comics_in_library(session: Session, library_id: int) -> List[Comic]:
    """Get all comics in a library"""
    return session.query(Comic).filter_by(library_id=library_id).all()


def get_comics_in_folder(session: Session, folder_id: int, library_id: Optional[int] = None) -> List[Comic]:
    """
    Get all comics in a folder

    Args:
        session: Database session
        folder_id: ID of the folder
        library_id: Optional library ID to filter by (recommended to avoid cross-library issues)
    """
    query = session.query(Comic).filter_by(folder_id=folder_id)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.all()


def search_comics(session: Session, library_id: int, query_str: str) -> List[Comic]:
    """
    Search for comics in a library by metadata

    Searches across multiple fields:
    - title
    - series
    - filename
    - writer
    - publisher
    - description

    Args:
        session: Database session
        library_id: ID of the library to search in
        query_str: Search query string (case-insensitive)

    Returns:
        List of matching comics, ordered by relevance (title/series matches first)
    """
    if not query_str or not query_str.strip():
        return []

    # Normalize search query (case-insensitive)
    search_pattern = f"%{query_str.strip()}%"

    # Build query with OR conditions across multiple fields
    query = session.query(Comic).filter(
        Comic.library_id == library_id
    ).filter(
        (Comic.title.ilike(search_pattern)) |
        (Comic.series.ilike(search_pattern)) |
        (Comic.filename.ilike(search_pattern)) |
        (Comic.writer.ilike(search_pattern)) |
        (Comic.publisher.ilike(search_pattern)) |
        (Comic.description.ilike(search_pattern)) |
        (Comic.penciller.ilike(search_pattern)) |
        (Comic.inker.ilike(search_pattern)) |
        (Comic.colorist.ilike(search_pattern)) |
        (Comic.genre.ilike(search_pattern)) |
        (Comic.characters.ilike(search_pattern))
    )

    # Order by relevance: title/series matches first, then filename
    # We use case statements to prioritize matches in more important fields
    results = query.all()

    # Sort results by relevance (title > series > filename > others)
    def relevance_score(comic):
        q_lower = query_str.lower()
        score = 0
        if comic.title and q_lower in comic.title.lower():
            score += 100
        if comic.series and q_lower in comic.series.lower():
            score += 50
        if comic.filename and q_lower in comic.filename.lower():
            score += 25
        return score

    results.sort(key=relevance_score, reverse=True)

    return results


def get_sibling_comics(session: Session, comic_id: int) -> tuple[Optional[int], Optional[int]]:
    """
    Get the previous and next comic IDs in the same folder.
    Returns (previous_comic_id, next_comic_id)

    Comics are ordered alphabetically by filename within the folder.
    This matches YACReader's navigation behavior.
    """
    comic = get_comic_by_id(session, comic_id)
    if not comic:
        return (None, None)

    # Get all comics in the same folder, ordered by filename
    comics = (
        session.query(Comic)
        .filter_by(folder_id=comic.folder_id)
        .order_by(Comic.filename)
        .all()
    )

    # Find current comic's position
    current_index = None
    for i, c in enumerate(comics):
        if c.id == comic_id:
            current_index = i
            break

    if current_index is None:
        return (None, None)

    # Get previous and next
    prev_id = comics[current_index - 1].id if current_index > 0 else None
    next_id = comics[current_index + 1].id if current_index < len(comics) - 1 else None

    return (prev_id, next_id)


# ============================================================================
# Folder Operations
# ============================================================================

def create_folder(
    session: Session,
    library_id: int,
    path: str,
    name: str,
    parent_id: Optional[int] = None
) -> Folder:
    """Create a new folder"""
    now = int(time.time())

    folder = Folder(
        library_id=library_id,
        parent_id=parent_id,
        path=str(Path(path).resolve()),
        name=name,
        created_at=now,
        updated_at=now
    )

    session.add(folder)
    session.flush()  # Flush to get the ID without committing

    logger.debug(f"Created folder: {name}")
    return folder


def get_folder_by_id(session: Session, folder_id: int) -> Optional[Folder]:
    """Get folder by ID"""
    return session.query(Folder).filter_by(id=folder_id).first()


def get_folder_by_path(session: Session, library_id: int, path: str) -> Optional[Folder]:
    """Get folder by path"""
    return session.query(Folder).filter_by(
        library_id=library_id,
        path=str(Path(path).resolve())
    ).first()


def get_folders_in_library(session: Session, library_id: int) -> List[Folder]:
    """Get all folders in a library"""
    return session.query(Folder).filter_by(library_id=library_id).all()


def get_or_create_root_folder(session: Session, library_id: int, library_path: str) -> Folder:
    """
    Get or create the virtual root folder (ID=1) for a library.

    YACReader convention: Every library has a virtual root folder with ID=1
    that acts as a container for top-level folders and comics, but is never
    shown in the UI.

    Args:
        session: Database session
        library_id: Library ID
        library_path: Path to the library root

    Returns:
        Root folder (ID=1 for the library)
    """
    # Check if root folder already exists (ID=1)
    root = session.query(Folder).filter_by(id=1, library_id=library_id).first()

    if root:
        return root

    # Check if ANY folder with ID=1 exists (might be from another library)
    existing_id_1 = session.query(Folder).filter_by(id=1).first()

    if existing_id_1:
        # ID=1 is taken by another library's root folder
        # This is OK - each library can have its own root folder
        # But we need to find this library's root folder (parent_id=None with special marker)
        root = session.query(Folder).filter_by(
            library_id=library_id,
            parent_id=None,
            name="__ROOT__"
        ).first()

        if root:
            return root

    # Create new root folder
    now = int(time.time())

    # Try to create with ID=1
    root = Folder(
        library_id=library_id,
        parent_id=None,  # Root has no parent
        path=str(Path(library_path).resolve()),
        name="__ROOT__",  # Special marker name
        created_at=now,
        updated_at=now
    )

    session.add(root)
    session.flush()  # Flush to get the auto-generated ID

    # Check if we got ID=1
    if root.id == 1:
        logger.debug(f"Created root folder with ID=1 for library {library_id}")
        return root
    else:
        # We didn't get ID=1, this means another library already has it
        # Keep this root folder but mark it specially
        logger.debug(f"Created root folder with ID={root.id} for library {library_id} (ID=1 taken)")
        return root


def get_subfolders(session: Session, parent_id: int) -> List[Folder]:
    """Get immediate subfolders of a folder"""
    return session.query(Folder).filter_by(parent_id=parent_id).all()


def get_first_comic_recursive(session: Session, folder_id: int, library_id: int):
    """
    Recursively find the first comic in a folder hierarchy.

    If the folder contains comics, return the first one (ordered by filename).
    If the folder contains only subfolders, recursively search the first subfolder.

    Args:
        session: Database session
        folder_id: ID of the folder to search in
        library_id: ID of the library (for scoping)

    Returns:
        Comic object or None if no comics found
    """
    from .models import Comic

    # First, try to find a comic directly in this folder
    first_comic = session.query(Comic).filter_by(
        library_id=library_id,
        folder_id=folder_id
    ).order_by(Comic.filename).first()

    if first_comic:
        return first_comic

    # If no comics in this folder, recursively search subfolders
    subfolders = session.query(Folder).filter_by(
        parent_id=folder_id
    ).order_by(Folder.name).all()

    for subfolder in subfolders:
        comic = get_first_comic_recursive(session, subfolder.id, library_id)
        if comic:
            return comic

    return None


# ============================================================================
# User Operations
# ============================================================================

def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return session.query(User).filter_by(username=username).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return session.query(User).filter_by(id=user_id).first()


# ============================================================================
# Session Operations
# ============================================================================

def create_session(
    session: Session,
    user_id: int,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    expires_in: int = 86400  # 24 hours
) -> DBSession:
    """Create a new session"""
    now = int(time.time())

    db_session = DBSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        user_agent=user_agent,
        ip_address=ip_address,
        created_at=now,
        last_activity_at=now,
        expires_at=now + expires_in
    )

    session.add(db_session)
    session.flush()  # Flush to get the ID without committing

    return db_session


def get_session_by_id(session: Session, session_id: str) -> Optional[DBSession]:
    """Get session by ID"""
    return session.query(DBSession).filter_by(id=session_id).first()


def update_session_activity(session: Session, session_id: str):
    """Update session last activity timestamp"""
    db_session = get_session_by_id(session, session_id)
    if db_session:
        db_session.last_activity_at = int(time.time())
        session.flush()  # Flush changes without committing


def cleanup_expired_sessions(session: Session):
    """Remove expired sessions"""
    now = int(time.time())
    session.query(DBSession).filter(DBSession.expires_at < now).delete()
    session.flush()  # Flush changes without committing


# ============================================================================
# Statistics
# ============================================================================

def get_library_stats(session: Session, library_id: int) -> dict:
    """Get statistics for a library"""
    comic_count = session.query(func.count(Comic.id)).filter_by(library_id=library_id).scalar()
    folder_count = session.query(func.count(Folder.id)).filter_by(library_id=library_id).scalar()

    return {
        'comic_count': comic_count or 0,
        'folder_count': folder_count or 0,
    }


# ============================================================================
# Reading Progress Operations
# ============================================================================

def update_reading_progress(
    session: Session,
    user_id: int,
    comic_id: int,
    current_page: int,
    total_pages: int
) -> ReadingProgress:
    """
    Update or create reading progress for a comic

    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID
        current_page: Current page number (0-indexed)
        total_pages: Total number of pages

    Returns:
        ReadingProgress object
    """
    now = int(time.time())

    # Calculate progress percentage
    progress_percent = (current_page / total_pages * 100) if total_pages > 0 else 0
    is_completed = current_page >= total_pages - 1  # Last page

    # Get existing progress or create new
    progress = session.query(ReadingProgress).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()

    if progress:
        # Update existing
        progress.current_page = current_page
        progress.total_pages = total_pages
        progress.progress_percent = progress_percent
        progress.last_read_at = now

        if is_completed and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = now
    else:
        # Create new
        progress = ReadingProgress(
            user_id=user_id,
            comic_id=comic_id,
            current_page=current_page,
            total_pages=total_pages,
            progress_percent=progress_percent,
            is_completed=is_completed,
            started_at=now,
            last_read_at=now,
            completed_at=now if is_completed else None
        )
        session.add(progress)

    session.flush()  # Flush changes without committing

    logger.debug(f"Updated reading progress for comic {comic_id}: page {current_page}/{total_pages}")
    return progress


def get_reading_progress(
    session: Session,
    user_id: int,
    comic_id: int
) -> Optional[ReadingProgress]:
    """Get reading progress for a specific comic"""
    return session.query(ReadingProgress).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()


def get_continue_reading(
    session: Session,
    user_id: int,
    limit: int = 10
) -> List[tuple[ReadingProgress, Comic]]:
    """
    Get recently read comics for "continue reading" feature

    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of results (default: 10)

    Returns:
        List of tuples (ReadingProgress, Comic) ordered by most recently read
    """
    results = session.query(ReadingProgress, Comic).join(
        Comic, ReadingProgress.comic_id == Comic.id
    ).filter(
        ReadingProgress.user_id == user_id,
        ReadingProgress.is_completed == False  # Only in-progress comics
    ).order_by(
        ReadingProgress.last_read_at.desc()
    ).limit(limit).all()

    return results


def get_recently_completed(
    session: Session,
    user_id: int,
    limit: int = 10
) -> List[tuple[ReadingProgress, Comic]]:
    """
    Get recently completed comics

    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of results (default: 10)

    Returns:
        List of tuples (ReadingProgress, Comic) ordered by most recently completed
    """
    results = session.query(ReadingProgress, Comic).join(
        Comic, ReadingProgress.comic_id == Comic.id
    ).filter(
        ReadingProgress.user_id == user_id,
        ReadingProgress.is_completed == True
    ).order_by(
        ReadingProgress.completed_at.desc()
    ).limit(limit).all()

    return results


# ============================================================================
# Cover Operations
# ============================================================================

def create_cover(
    session: Session,
    comic_id: int,
    cover_type: str,
    page_number: int,
    jpeg_path: str,
    webp_path: Optional[str] = None
) -> Cover:
    """
    Create a new cover entry

    Args:
        session: Database session
        comic_id: Comic ID
        cover_type: Type of cover ('auto' or 'custom')
        page_number: Page number used for cover (0-indexed)
        jpeg_path: Path to JPEG thumbnail
        webp_path: Path to WebP thumbnail (optional)

    Returns:
        Cover object
    """
    now = int(time.time())

    # Check if cover of this type already exists
    existing_cover = session.query(Cover).filter_by(
        comic_id=comic_id,
        type=cover_type
    ).first()

    if existing_cover:
        # Update existing
        existing_cover.page_number = page_number
        existing_cover.jpeg_path = jpeg_path
        existing_cover.webp_path = webp_path
        existing_cover.generated_at = now
        session.flush()  # Flush changes without committing
        return existing_cover

    # Create new
    cover = Cover(
        comic_id=comic_id,
        type=cover_type,
        page_number=page_number,
        jpeg_path=jpeg_path,
        webp_path=webp_path,
        generated_at=now
    )

    session.add(cover)
    session.flush()  # Flush to get the ID without committing

    logger.debug(f"Created {cover_type} cover for comic {comic_id} from page {page_number}")
    return cover


def get_cover(session: Session, comic_id: int, cover_type: str = 'auto') -> Optional[Cover]:
    """
    Get cover for a comic

    Args:
        session: Database session
        comic_id: Comic ID
        cover_type: Type of cover ('auto' or 'custom')

    Returns:
        Cover object or None
    """
    return session.query(Cover).filter_by(
        comic_id=comic_id,
        type=cover_type
    ).first()


def get_best_cover(session: Session, comic_id: int) -> Optional[Cover]:
    """
    Get the best cover for a comic (custom if available, otherwise auto)

    Args:
        session: Database session
        comic_id: Comic ID

    Returns:
        Cover object or None
    """
    # Try custom first
    custom = get_cover(session, comic_id, 'custom')
    if custom:
        return custom

    # Fall back to auto
    return get_cover(session, comic_id, 'auto')


def delete_cover(session: Session, comic_id: int, cover_type: str):
    """
    Delete a cover

    Args:
        session: Database session
        comic_id: Comic ID
        cover_type: Type of cover to delete
    """
    cover = get_cover(session, comic_id, cover_type)
    if cover:
        # Delete files
        jpeg_path = Path(cover.jpeg_path)
        if jpeg_path.exists():
            jpeg_path.unlink()

        if cover.webp_path:
            webp_path = Path(cover.webp_path)
            if webp_path.exists():
                webp_path.unlink()

        # Delete from database
        session.delete(cover)
        session.flush()  # Flush changes without committing
        logger.debug(f"Deleted {cover_type} cover for comic {comic_id}")


# ============================================================================
# FAVORITES OPERATIONS (YACReader Compatibility)
# ============================================================================

def add_favorite(session: Session, user_id: int, library_id: int, comic_id: int):
    """
    Add a comic to user's favorites

    Args:
        session: Database session
        user_id: User ID
        library_id: Library ID
        comic_id: Comic ID

    Returns:
        Favorite object
    """
    from .models import Favorite

    # Check if already favorited
    existing = session.query(Favorite).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()

    if existing:
        return existing

    favorite = Favorite(
        user_id=user_id,
        library_id=library_id,
        comic_id=comic_id,
        created_at=int(time.time())
    )

    session.add(favorite)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Added favorite: user={user_id}, comic={comic_id}")
    return favorite


def remove_favorite(session: Session, user_id: int, comic_id: int) -> bool:
    """
    Remove a comic from user's favorites

    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID

    Returns:
        True if removed, False if not found
    """
    from .models import Favorite

    favorite = session.query(Favorite).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()

    if favorite:
        session.delete(favorite)
        session.flush()  # Flush changes without committing
        logger.debug(f"Removed favorite: user={user_id}, comic={comic_id}")
        return True

    return False


def get_user_favorites(session: Session, user_id: int, library_id: int) -> List[Comic]:
    """
    Get all favorite comics for a user in a library

    Args:
        session: Database session
        user_id: User ID
        library_id: Library ID

    Returns:
        List of Comic objects
    """
    from .models import Favorite

    favorites = session.query(Comic).join(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.library_id == library_id
    ).order_by(Favorite.created_at.desc()).all()

    return favorites


def is_favorite(session: Session, user_id: int, comic_id: int) -> bool:
    """
    Check if a comic is in user's favorites

    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID

    Returns:
        True if favorited, False otherwise
    """
    from .models import Favorite

    count = session.query(Favorite).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).count()

    return count > 0


# ============================================================================
# LABELS/TAGS OPERATIONS (YACReader Compatibility)
# ============================================================================

def create_label(session: Session, library_id: int, name: str, color_id: int = 0) -> 'Label':
    """
    Create a new label/tag

    Args:
        session: Database session
        library_id: Library ID
        name: Label name
        color_id: Color identifier (default: 0)

    Returns:
        Label object
    """
    from .models import Label

    # Check if label already exists
    existing = session.query(Label).filter_by(
        library_id=library_id,
        name=name
    ).first()

    if existing:
        return existing

    label = Label(
        library_id=library_id,
        name=name,
        color_id=color_id,
        position=0,
        created_at=int(time.time()),
        updated_at=int(time.time())
    )

    session.add(label)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Created label: library={library_id}, name={name}")
    return label


def get_label_by_id(session: Session, label_id: int) -> Optional['Label']:
    """
    Get label by ID

    Args:
        session: Database session
        label_id: Label ID

    Returns:
        Label object or None
    """
    from .models import Label
    return session.query(Label).filter_by(id=label_id).first()


def get_labels_in_library(session: Session, library_id: int) -> List['Label']:
    """
    Get all labels in a library

    Args:
        session: Database session
        library_id: Library ID

    Returns:
        List of Label objects
    """
    from .models import Label
    return session.query(Label).filter_by(library_id=library_id).order_by(Label.position, Label.name).all()


def delete_label(session: Session, label_id: int) -> bool:
    """
    Delete a label

    Args:
        session: Database session
        label_id: Label ID

    Returns:
        True if deleted, False if not found
    """
    from .models import Label

    label = get_label_by_id(session, label_id)
    if label:
        session.delete(label)
        session.flush()  # Flush changes without committing
        logger.debug(f"Deleted label: id={label_id}")
        return True

    return False


def add_label_to_comic(session: Session, comic_id: int, label_id: int):
    """
    Add a label to a comic

    Args:
        session: Database session
        comic_id: Comic ID
        label_id: Label ID

    Returns:
        ComicLabel object
    """
    from .models import ComicLabel

    # Check if already labeled
    existing = session.query(ComicLabel).filter_by(
        comic_id=comic_id,
        label_id=label_id
    ).first()

    if existing:
        return existing

    comic_label = ComicLabel(
        comic_id=comic_id,
        label_id=label_id,
        created_at=int(time.time())
    )

    session.add(comic_label)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Added label to comic: comic={comic_id}, label={label_id}")
    return comic_label


def remove_label_from_comic(session: Session, comic_id: int, label_id: int) -> bool:
    """
    Remove a label from a comic

    Args:
        session: Database session
        comic_id: Comic ID
        label_id: Label ID

    Returns:
        True if removed, False if not found
    """
    from .models import ComicLabel

    comic_label = session.query(ComicLabel).filter_by(
        comic_id=comic_id,
        label_id=label_id
    ).first()

    if comic_label:
        session.delete(comic_label)
        session.flush()  # Flush changes without committing
        logger.debug(f"Removed label from comic: comic={comic_id}, label={label_id}")
        return True

    return False


def get_comics_with_label(session: Session, label_id: int) -> List[Comic]:
    """
    Get all comics with a specific label

    Args:
        session: Database session
        label_id: Label ID

    Returns:
        List of Comic objects
    """
    from .models import ComicLabel

    comics = session.query(Comic).join(ComicLabel).filter(
        ComicLabel.label_id == label_id
    ).all()

    return comics


def get_comic_labels(session: Session, comic_id: int) -> List['Label']:
    """
    Get all labels for a comic

    Args:
        session: Database session
        comic_id: Comic ID

    Returns:
        List of Label objects
    """
    from .models import Label, ComicLabel

    labels = session.query(Label).join(ComicLabel).filter(
        ComicLabel.comic_id == comic_id
    ).all()

    return labels


# ============================================================================
# READING LISTS OPERATIONS (YACReader Compatibility)
# ============================================================================

def create_reading_list(
    session: Session,
    library_id: int,
    name: str,
    user_id: Optional[int] = None,
    description: Optional[str] = None,
    is_public: bool = False
) -> 'ReadingList':
    """
    Create a new reading list

    Args:
        session: Database session
        library_id: Library ID
        name: Reading list name
        user_id: Owner user ID (optional for public lists)
        description: Description (optional)
        is_public: Whether list is public

    Returns:
        ReadingList object
    """
    from .models import ReadingList

    reading_list = ReadingList(
        library_id=library_id,
        user_id=user_id,
        name=name,
        description=description,
        is_public=is_public,
        position=0,
        created_at=int(time.time()),
        updated_at=int(time.time())
    )

    session.add(reading_list)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Created reading list: library={library_id}, name={name}")
    return reading_list


def get_reading_list_by_id(session: Session, list_id: int) -> Optional['ReadingList']:
    """
    Get reading list by ID

    Args:
        session: Database session
        list_id: Reading list ID

    Returns:
        ReadingList object or None
    """
    from .models import ReadingList
    return session.query(ReadingList).filter_by(id=list_id).first()


def get_reading_lists_in_library(session: Session, library_id: int, user_id: Optional[int] = None) -> List['ReadingList']:
    """
    Get all reading lists in a library

    Args:
        session: Database session
        library_id: Library ID
        user_id: Filter by user ID (optional, includes public lists)

    Returns:
        List of ReadingList objects
    """
    from .models import ReadingList

    query = session.query(ReadingList).filter_by(library_id=library_id)

    if user_id is not None:
        # Get user's lists + public lists
        from sqlalchemy import or_
        query = query.filter(
            or_(
                ReadingList.user_id == user_id,
                ReadingList.is_public == True
            )
        )
    else:
        # Get all public lists
        query = query.filter(ReadingList.is_public == True)

    return query.order_by(ReadingList.position, ReadingList.name).all()


def delete_reading_list(session: Session, list_id: int) -> bool:
    """
    Delete a reading list

    Args:
        session: Database session
        list_id: Reading list ID

    Returns:
        True if deleted, False if not found
    """
    from .models import ReadingList

    reading_list = get_reading_list_by_id(session, list_id)
    if reading_list:
        session.delete(reading_list)
        session.flush()  # Flush changes without committing
        logger.debug(f"Deleted reading list: id={list_id}")
        return True

    return False


def add_comic_to_reading_list(session: Session, list_id: int, comic_id: int, position: Optional[int] = None):
    """
    Add a comic to a reading list

    Args:
        session: Database session
        list_id: Reading list ID
        comic_id: Comic ID
        position: Position in list (optional, appends to end if not specified)

    Returns:
        ReadingListItem object
    """
    from .models import ReadingListItem

    # Check if already in list
    existing = session.query(ReadingListItem).filter_by(
        reading_list_id=list_id,
        comic_id=comic_id
    ).first()

    if existing:
        return existing

    # Get next position if not specified
    if position is None:
        max_position = session.query(func.max(ReadingListItem.position)).filter_by(
            reading_list_id=list_id
        ).scalar() or -1
        position = max_position + 1

    item = ReadingListItem(
        reading_list_id=list_id,
        comic_id=comic_id,
        position=position,
        added_at=int(time.time())
    )

    session.add(item)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Added comic to reading list: list={list_id}, comic={comic_id}, position={position}")
    return item


def remove_comic_from_reading_list(session: Session, list_id: int, comic_id: int) -> bool:
    """
    Remove a comic from a reading list

    Args:
        session: Database session
        list_id: Reading list ID
        comic_id: Comic ID

    Returns:
        True if removed, False if not found
    """
    from .models import ReadingListItem

    item = session.query(ReadingListItem).filter_by(
        reading_list_id=list_id,
        comic_id=comic_id
    ).first()

    if item:
        session.delete(item)
        session.flush()  # Flush changes without committing
        logger.debug(f"Removed comic from reading list: list={list_id}, comic={comic_id}")
        return True

    return False


def get_reading_list_comics(session: Session, list_id: int) -> List[Comic]:
    """
    Get all comics in a reading list (ordered by position)

    Args:
        session: Database session
        list_id: Reading list ID

    Returns:
        List of Comic objects in order
    """
    from .models import ReadingListItem

    comics = session.query(Comic).join(ReadingListItem).filter(
        ReadingListItem.reading_list_id == list_id
    ).order_by(ReadingListItem.position).all()

    return comics
