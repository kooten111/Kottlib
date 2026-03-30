"""
Database connection and session management.

Provides the Database class for managing connections to the SQLite database.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Generator, Union
from contextlib import contextmanager

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from .models import Base, User
from .operations.user import hash_password
from .paths import get_default_db_path


logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""

    def __init__(self, db_path: Optional[Union[Path, str]] = None, echo: bool = False) -> None:
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file (None = default location)
            echo: If True, log all SQL statements
        """
        if db_path is None:
            db_path = get_default_db_path()

        self.db_path = Path(db_path)

        # Ensure parent directory exists before creating database
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_url = f"sqlite:///{self.db_path}"

        # Create engine
        # Use NullPool for SQLite in multi-threaded scenarios to avoid connection sharing issues
        # Each session gets its own connection that's immediately returned after use
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

    def init_db(self) -> None:
        """Initialize database schema (create tables)."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database schema created")

        # Run migrations to ensure schema is up to date
        self._run_migrations()

        # Create default admin user if not exists
        # Use try-except to handle race condition in multi-process environments
        try:
            with self.get_session() as session:
                admin = session.query(User).filter_by(username='admin').first()
                if not admin:
                    admin = User(
                        username='admin',
                        password_hash=hash_password('changeme'),
                        is_admin=True,
                        is_active=True,
                        created_at=int(time.time())
                    )
                    session.add(admin)
                    session.commit()
                    logger.info("Created default admin user")
        except IntegrityError:
            # Admin user already exists (race condition), silently ignore
            logger.debug("Admin user already exists (created by another process)")

    def _run_migrations(self) -> None:
        """
        Run database migrations to update schema for existing databases.

        This ensures that databases created with older versions of the code
        are updated to match the current schema.
        """
        try:
            with self.engine.connect() as conn:
                # Migration 1: Add missing columns to sessions table
                # Check if device_type column exists
                result = conn.execute(text("PRAGMA table_info(sessions)")).fetchall()
                column_names = [row[1] for row in result]

                if 'device_type' not in column_names:
                    logger.info("Running migration: Adding device_type to sessions table")
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN device_type TEXT NULL"))
                    conn.commit()
                    logger.info("Migration complete: device_type column added")

                if 'display_type' not in column_names:
                    logger.info("Running migration: Adding display_type to sessions table")
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN display_type TEXT NULL"))
                    conn.commit()
                    logger.info("Migration complete: display_type column added")

                if 'downloaded_comics' not in column_names:
                    logger.info("Running migration: Adding downloaded_comics to sessions table")
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN downloaded_comics TEXT NULL"))
                    conn.commit()
                    logger.info("Migration complete: downloaded_comics column added")

                # Migration 2: Add cover source columns
                result = conn.execute(text("PRAGMA table_info(covers)")).fetchall()
                cover_columns = [row[1] for row in result]

                if 'source' not in cover_columns:
                    logger.info("Running migration: Adding source to covers table")
                    conn.execute(text("ALTER TABLE covers ADD COLUMN source TEXT NOT NULL DEFAULT 'archive'"))
                    conn.commit()
                    logger.info("Migration complete: source column added")

                if 'source_url' not in cover_columns:
                    logger.info("Running migration: Adding source_url to covers table")
                    conn.execute(text("ALTER TABLE covers ADD COLUMN source_url TEXT NULL"))
                    conn.commit()
                    logger.info("Migration complete: source_url column added")

                # Migration 3: Create favorites table if missing (was only in schema_v3.sql)
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='favorites'")).fetchone()
                if not result:
                    logger.info("Running migration: Creating favorites table")
                    conn.execute(text("""
                        CREATE TABLE favorites (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL DEFAULT 1,
                            library_id INTEGER NOT NULL,
                            comic_id INTEGER NOT NULL,
                            created_at INTEGER NOT NULL,
                            FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
                            UNIQUE(user_id, comic_id)
                        )
                    """))
                    conn.execute(text("CREATE INDEX idx_favorites_user ON favorites(user_id)"))
                    conn.execute(text("CREATE INDEX idx_favorites_comic ON favorites(comic_id)"))
                    conn.commit()
                    logger.info("Migration complete: favorites table created")

        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            # Don't fail startup if migrations fail - the app might still work
            # This is a best-effort attempt to update the schema

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session (context manager).

        Usage:
            with db.get_session() as session:
                # Use session here
                pass
        
        Yields:
            Session: SQLAlchemy database session
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

    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()
