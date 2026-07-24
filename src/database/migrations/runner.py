"""
Ordered migration runner for startup schema updates.

Search-index migrations (FTS5) are intentionally excluded — run those via
the admin API when needed.
"""

import logging
from typing import Callable, List, Optional, Tuple

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from . import add_cover_source_columns, add_folder_last_content_at, inline_schema

logger = logging.getLogger(__name__)

MigrationFn = Callable[[Session], None]

STARTUP_MIGRATIONS: List[Tuple[str, MigrationFn]] = [
    ("inline_schema", inline_schema.upgrade),
    ("cover_source_columns", add_cover_source_columns.upgrade),
    ("folder_last_content_at", add_folder_last_content_at.upgrade),
]


def run_startup_migrations(
    engine: Engine, migrations: Optional[List[Tuple[str, MigrationFn]]] = None
) -> None:
    """
    Run idempotent startup migrations in order.

    Individual migration modules may commit internally; failures are logged
    but do not abort server startup (best-effort schema alignment).
    """
    steps = migrations if migrations is not None else STARTUP_MIGRATIONS
    session_factory = sessionmaker(bind=engine)

    for name, migrate in steps:
        try:
            logger.info("Running migration: %s", name)
            with session_factory() as session:
                migrate(session)
                session.commit()
            logger.info("Migration complete: %s", name)
        except Exception as exc:
            logger.error("Migration %s failed: %s", name, exc)
