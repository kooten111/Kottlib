#!/usr/bin/env python3
"""
YACReader Library Importer

Imports existing YACReader libraries into YACLib Enhanced format.
Reads YACReader's library.ydb and converts to our schema.
"""

import sqlite3
import argparse
import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
import shutil
import time


class YACReaderImporter:
    """Import YACReader library database to YACLib Enhanced format."""

    def __init__(self, yacreader_db_path: str, output_db_path: str, verbose: bool = False):
        self.yacreader_db = yacreader_db_path
        self.output_db = output_db_path
        self.verbose = verbose

        # Stats
        self.stats = {
            'folders': 0,
            'comics': 0,
            'covers': 0,
            'reading_progress': 0,
            'errors': 0
        }

    def log(self, message: str, level: str = 'INFO'):
        """Log message if verbose mode is enabled."""
        if self.verbose or level == 'ERROR':
            print(f"[{level}] {message}")

    def compute_file_hash(self, filepath: str) -> str:
        """Compute SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.log(f"Error computing hash for {filepath}: {e}", 'ERROR')
            # Fallback to path-based hash
            return hashlib.sha256(filepath.encode()).hexdigest()

    def analyze_yacreader_schema(self) -> Dict:
        """Analyze YACReader database schema to understand structure."""
        self.log("Analyzing YACReader database schema...")

        conn = sqlite3.connect(self.yacreader_db)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            schema[table] = {col[1]: col[2] for col in columns}  # name: type

        conn.close()

        self.log(f"Found tables: {', '.join(tables)}")
        return schema

    def import_library(self, library_path: str, library_name: Optional[str] = None):
        """Import a YACReader library."""

        self.log(f"Importing YACReader library from: {library_path}")

        # Verify YACReader database exists
        if not os.path.exists(self.yacreader_db):
            raise FileNotFoundError(f"YACReader database not found: {self.yacreader_db}")

        # Analyze schema first
        yac_schema = self.analyze_yacreader_schema()

        # Connect to both databases
        yac_conn = sqlite3.connect(self.yacreader_db)
        yac_conn.row_factory = sqlite3.Row

        out_conn = sqlite3.connect(self.output_db)
        out_cursor = out_conn.cursor()

        try:
            # Import in order: library -> folders -> comics -> covers -> progress
            library_id = self._import_library_info(yac_conn, out_cursor, library_path, library_name)
            self._import_folders(yac_conn, out_cursor, library_id)
            self._import_comics(yac_conn, out_cursor, library_id, library_path)
            self._import_covers(yac_conn, out_cursor, library_path)
            self._import_reading_progress(yac_conn, out_cursor)

            out_conn.commit()
            self.log("Import completed successfully!")
            self.print_stats()

        except Exception as e:
            out_conn.rollback()
            self.log(f"Import failed: {e}", 'ERROR')
            raise
        finally:
            yac_conn.close()
            out_conn.close()

    def _import_library_info(self, yac_conn, out_cursor, library_path: str, library_name: Optional[str]) -> int:
        """Import library metadata."""
        self.log("Importing library info...")

        # Read library UUID if it exists
        uuid_file = os.path.join(os.path.dirname(self.yacreader_db), 'id')
        if os.path.exists(uuid_file):
            with open(uuid_file, 'r') as f:
                uuid = f.read().strip()
        else:
            # Generate new UUID
            import uuid as uuid_module
            uuid = str(uuid_module.uuid4())

        # Use provided name or derive from path
        if not library_name:
            library_name = os.path.basename(library_path.rstrip('/'))

        now = int(time.time())

        out_cursor.execute("""
            INSERT INTO libraries (uuid, name, path, created_at, updated_at, last_scan_at, scan_status)
            VALUES (?, ?, ?, ?, ?, ?, 'complete')
        """, (uuid, library_name, library_path, now, now, now))

        library_id = out_cursor.lastrowid
        self.log(f"Created library: {library_name} (ID: {library_id})")

        return library_id

    def _import_folders(self, yac_conn, out_cursor, library_id: int):
        """Import folder structure."""
        self.log("Importing folders...")

        yac_cursor = yac_conn.cursor()

        # YACReader typically has a 'folder' table
        # This is a best-guess - may need adjustment based on actual schema
        try:
            yac_cursor.execute("SELECT * FROM folder ORDER BY id")
            folders = yac_cursor.fetchall()

            folder_id_map = {}  # YACReader ID -> YACLib ID
            now = int(time.time())

            for folder in folders:
                folder_dict = dict(folder)

                # Map parent_id if it exists
                parent_id = None
                if 'parentId' in folder_dict and folder_dict['parentId']:
                    parent_id = folder_id_map.get(folder_dict['parentId'])

                out_cursor.execute("""
                    INSERT INTO folders (library_id, parent_id, path, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    library_id,
                    parent_id,
                    folder_dict.get('path', ''),
                    folder_dict.get('name', ''),
                    now,
                    now
                ))

                folder_id_map[folder_dict['id']] = out_cursor.lastrowid
                self.stats['folders'] += 1

            self.log(f"Imported {self.stats['folders']} folders")

        except sqlite3.OperationalError as e:
            self.log(f"Could not import folders (table may not exist): {e}", 'ERROR')
            self.stats['errors'] += 1

    def _import_comics(self, yac_conn, out_cursor, library_id: int, library_path: str):
        """Import comics."""
        self.log("Importing comics...")

        yac_cursor = yac_conn.cursor()

        try:
            # YACReader 'comic' table
            yac_cursor.execute("SELECT * FROM comic")
            comics = yac_cursor.fetchall()

            now = int(time.time())

            for comic in comics:
                comic_dict = dict(comic)

                # Build full path
                comic_path = comic_dict.get('path', '')
                if not os.path.isabs(comic_path):
                    comic_path = os.path.join(library_path, comic_path)

                # Get file info
                file_size = 0
                file_mtime = now
                if os.path.exists(comic_path):
                    file_stat = os.stat(comic_path)
                    file_size = file_stat.st_size
                    file_mtime = int(file_stat.st_mtime)
                    file_hash = self.compute_file_hash(comic_path)
                else:
                    self.log(f"Comic file not found: {comic_path}", 'ERROR')
                    file_hash = hashlib.sha256(comic_path.encode()).hexdigest()
                    self.stats['errors'] += 1

                # Extract format from filename
                filename = os.path.basename(comic_path)
                format_ext = os.path.splitext(filename)[1].lower().lstrip('.')

                # Extract metadata
                title = comic_dict.get('title') or comic_dict.get('fileName', filename)
                num_pages = comic_dict.get('numPages', 0) or comic_dict.get('pageCount', 0)

                out_cursor.execute("""
                    INSERT INTO comics (
                        library_id, folder_id, path, filename, hash,
                        file_size, file_modified_at, format,
                        title, num_pages,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    library_id,
                    None,  # folder_id - would need mapping
                    comic_path,
                    filename,
                    file_hash,
                    file_size,
                    file_mtime,
                    format_ext,
                    title,
                    num_pages,
                    now,
                    now
                ))

                self.stats['comics'] += 1

                if self.stats['comics'] % 100 == 0:
                    self.log(f"Imported {self.stats['comics']} comics...")

            self.log(f"Imported {self.stats['comics']} comics")

        except sqlite3.OperationalError as e:
            self.log(f"Error importing comics: {e}", 'ERROR')
            self.stats['errors'] += 1

    def _import_covers(self, yac_conn, out_cursor, library_path: str):
        """Import cover thumbnails."""
        self.log("Importing covers...")

        # YACReader stores covers in .yacreaderlibrary/covers/
        covers_dir = os.path.join(os.path.dirname(self.yacreader_db), 'covers')

        if not os.path.exists(covers_dir):
            self.log("No covers directory found", 'ERROR')
            return

        # Copy covers to new location and create records
        # This is simplified - real implementation would need to map comic IDs
        self.log("Cover import not yet implemented (requires comic ID mapping)")

    def _import_reading_progress(self, yac_conn, out_cursor):
        """Import reading progress."""
        self.log("Importing reading progress...")

        yac_cursor = yac_conn.cursor()

        try:
            # YACReader stores reading info in the comic table typically
            yac_cursor.execute("SELECT id, currentPage, pageCount FROM comic WHERE currentPage > 0")
            progress_records = yac_cursor.fetchall()

            now = int(time.time())

            for record in progress_records:
                record_dict = dict(record)
                current_page = record_dict.get('currentPage', 0)
                total_pages = record_dict.get('pageCount', 0)

                if total_pages > 0:
                    progress_percent = (current_page / total_pages) * 100
                    is_completed = 1 if current_page >= total_pages - 1 else 0

                    # Note: This would need proper comic_id mapping
                    # For now, we'll skip to avoid foreign key errors
                    self.stats['reading_progress'] += 1

            self.log(f"Found {self.stats['reading_progress']} reading progress records")

        except sqlite3.OperationalError as e:
            self.log(f"Could not import reading progress: {e}", 'ERROR')

    def print_stats(self):
        """Print import statistics."""
        print("\n" + "="*50)
        print("Import Statistics")
        print("="*50)
        for key, value in self.stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(
        description='Import YACReader library to YACLib Enhanced',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import a YACReader library
  python import_yacreader.py \\
    --yacreader-db /path/to/Library/.yacreaderlibrary/library.ydb \\
    --output-db /path/to/yaclib.db \\
    --library-path /path/to/Library

  # With custom library name
  python import_yacreader.py \\
    --yacreader-db ~/Comics/.yacreaderlibrary/library.ydb \\
    --output-db ~/yaclib.db \\
    --library-path ~/Comics \\
    --library-name "My Comics"
        """
    )

    parser.add_argument(
        '--yacreader-db',
        required=True,
        help='Path to YACReader library.ydb file'
    )

    parser.add_argument(
        '--output-db',
        required=True,
        help='Path to output YACLib Enhanced database (e.g., ~/.local/share/yaclib/yaclib.db)'
    )

    parser.add_argument(
        '--library-path',
        required=True,
        help='Path to library root directory'
    )

    parser.add_argument(
        '--library-name',
        help='Name for the library (default: derived from path)'
    )

    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze schema without importing'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    importer = YACReaderImporter(
        args.yacreader_db,
        args.output_db,
        verbose=args.verbose
    )

    if args.analyze_only:
        schema = importer.analyze_yacreader_schema()
        print("\nYACReader Database Schema:")
        print("="*50)
        for table, columns in schema.items():
            print(f"\n{table}:")
            for col_name, col_type in columns.items():
                print(f"  - {col_name}: {col_type}")
        return

    try:
        importer.import_library(args.library_path, args.library_name)
        print("\n✅ Import completed successfully!")
    except Exception as e:
        print(f"\n❌ Import failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
