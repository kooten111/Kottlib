"""Tests for the migration runner."""

from sqlalchemy import text

from src.database.migrations.runner import run_startup_migrations, STARTUP_MIGRATIONS


def test_startup_migrations_are_idempotent(test_db):
    engine = test_db.engine

    run_startup_migrations(engine)
    run_startup_migrations(engine)

    with engine.connect() as conn:
        session_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(sessions)")).fetchall()]
        cover_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(covers)")).fetchall()]
        favorites = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='favorites'")
        ).fetchone()

    assert "device_type" in session_cols
    assert "source" in cover_cols
    assert "source_url" in cover_cols
    assert favorites is not None


def test_startup_migration_list_order():
    names = [name for name, _ in STARTUP_MIGRATIONS]
    assert names == ["inline_schema", "cover_source_columns"]
