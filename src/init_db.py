"""
Database Initialization Script

Run this script before starting the server to ensure the database schema
is created and initial data is populated. This avoids concurrency issues
when running the server with multiple workers.
"""

import logging
from pathlib import Path
import sys
import os

# Add project root and src directory to path to allow imports
# The project root is needed for the 'src' package to be recognized
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.dirname(__file__)
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

from database import Database, get_default_db_path
from config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Initialize the database"""
    logger.info("Initializing database...")
    
    # Load config to get DB path
    config = get_config()
    db_path = config.database.path or get_default_db_path()
    
    logger.info(f"Database path: {db_path}")
    
    # Initialize database
    db = Database(db_path, echo=config.database.echo)
    
    # Create tables and default data
    db.init_db()
    
    logger.info("Database initialization complete.")
    db.close()

if __name__ == "__main__":
    main()
