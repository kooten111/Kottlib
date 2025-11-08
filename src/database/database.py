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
        # Use StaticPool for SQLite to avoid threading issues
        self.engine = create_engine(
            self.db_url,
            echo=echo,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
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
    session.commit()
    session.refresh(library)

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
        session.commit()


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

    session.add(comic)
    session.commit()

    # Refresh to get database-generated values (may fail in multi-threaded context)
    try:
        session.refresh(comic)
    except Exception:
        # If refresh fails, we still have the comic object with the data we set
        pass

    logger.debug(f"Created comic: {filename}")
    return comic


def get_comic_by_id(session: Session, comic_id: int) -> Optional[Comic]:
    """Get comic by ID"""
    return session.query(Comic).filter_by(id=comic_id).first()


def get_comic_by_hash(session: Session, file_hash: str) -> Optional[Comic]:
    """Get comic by file hash"""
    return session.query(Comic).filter_by(hash=file_hash).first()


def get_comics_in_library(session: Session, library_id: int) -> List[Comic]:
    """Get all comics in a library"""
    return session.query(Comic).filter_by(library_id=library_id).all()


def get_comics_in_folder(session: Session, folder_id: int) -> List[Comic]:
    """Get all comics in a folder"""
    return session.query(Comic).filter_by(folder_id=folder_id).all()


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
    session.commit()
    session.refresh(folder)

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


def get_subfolders(session: Session, parent_id: int) -> List[Folder]:
    """Get immediate subfolders of a folder"""
    return session.query(Folder).filter_by(parent_id=parent_id).all()


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
    session.commit()
    session.refresh(db_session)

    return db_session


def get_session_by_id(session: Session, session_id: str) -> Optional[DBSession]:
    """Get session by ID"""
    return session.query(DBSession).filter_by(id=session_id).first()


def update_session_activity(session: Session, session_id: str):
    """Update session last activity timestamp"""
    db_session = get_session_by_id(session, session_id)
    if db_session:
        db_session.last_activity_at = int(time.time())
        session.commit()


def cleanup_expired_sessions(session: Session):
    """Remove expired sessions"""
    now = int(time.time())
    session.query(DBSession).filter(DBSession.expires_at < now).delete()
    session.commit()


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

    session.commit()
    session.refresh(progress)

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
        session.commit()
        session.refresh(existing_cover)
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
    session.commit()
    session.refresh(cover)

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
        session.commit()
        logger.debug(f"Deleted {cover_type} cover for comic {comic_id}")
