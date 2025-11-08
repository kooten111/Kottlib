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

from .models import Base, Library, Folder, Comic, Cover, User, Session as DBSession
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
