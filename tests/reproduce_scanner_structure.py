
import os
import shutil
import tempfile
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Constants from the plan
ARCHIVE_EXTS = {'.cbz', '.cbr', '.zip', '.rar', '.7z', '.epub'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

def classify_series_structure(series_path: Path) -> str:
    """
    Determines if a Series folder is Simple, Nested, or Unpacked
    based on the Hybrid Hierarchy rules.
    """
    try:
        # Get all items in the series folder
        contents = list(series_path.iterdir())
    except OSError:
        return "Error: Access Denied"

    if not contents:
        return "Empty Folder"

    # 1. Check for MODE 1: Simple Series
    # Logic: Does it contain archive files directly?
    has_archives = any(f.is_file() and f.suffix.lower() in ARCHIVE_EXTS for f in contents)
    if has_archives:
        return "Mode 1: Simple Series (Standard)"

    # Get list of sub-directories to check for Modes 2 and 3
    subdirs = [d for d in contents if d.is_dir()]
    
    if subdirs:
        # We verify the structure by checking the content of the first sub-directory found.
        # (Assumes consistent structure within a single series folder)
        first_subdir = subdirs[0]
        try:
            subdir_contents = list(first_subdir.iterdir())
            
            # 2. Check for MODE 2: Franchise Collection
            # Logic: Do the sub-directories contain archives?
            if any(f.is_file() and f.suffix.lower() in ARCHIVE_EXTS for f in subdir_contents):
                return "Mode 2: Franchise/Arc (Nested)"
            
            # 3. Check for MODE 3: Unpacked/Raw
            # Logic: Do the sub-directories contain images?
            if any(f.is_file() and f.suffix.lower() in IMAGE_EXTS for f in subdir_contents):
                return "Mode 3: Unpacked (Image-based)"

            # 4. Check for MODE 3: Unpacked/Raw (Nested in Chapter folder)
            # If we found directories but no archives/images, look one level deeper
            grandchild_subdirs = [d for d in subdir_contents if d.is_dir()]
            if grandchild_subdirs:
                first_grandchild = grandchild_subdirs[0]
                try:
                    grandchild_contents = list(first_grandchild.iterdir())
                    if any(f.is_file() and f.suffix.lower() in IMAGE_EXTS for f in grandchild_contents):
                         return "Mode 3: Unpacked (Image-based)"
                except OSError:
                    pass
                
        except OSError:
            return "Error: Subdir Access Denied"

    return "Unknown Structure"

def create_mock_library(base_path: Path):
    """Creates a mock library structure for testing"""
    
    # 1. Simple Series: Berserk
    berserk = base_path / "Berserk"
    berserk.mkdir()
    (berserk / "Berserk v01.cbz").touch()
    (berserk / "Berserk v02.cbz").touch()
    
    # 2. Franchise Collection: Batman
    batman = base_path / "Batman"
    batman.mkdir()
    
    # Arc 1: Night of Owls
    owls = batman / "Night of Owls"
    owls.mkdir()
    (owls / "Batman Vol 1.cbz").touch()
    
    # Arc 2: Catwoman
    catwoman = batman / "Batman - Catwoman"
    catwoman.mkdir()
    (catwoman / "001.cbz").touch()
    
    # 3. Unpacked Series: Gyaru Academy
    gyaru = base_path / "Transferred to the Gyaru Academy"
    gyaru.mkdir()
    
    vol1 = gyaru / "v01"
    vol1.mkdir()
    
    chap1 = vol1 / "c001"
    chap1.mkdir()
    (chap1 / "001.jpg").touch()
    (chap1 / "002.jpg").touch()

    # 4. Mixed/Edge Case: Empty Folder
    empty = base_path / "Empty Series"
    empty.mkdir()
    
    # 5. Mixed/Edge Case: Unknown (only text files)
    unknown = base_path / "Text Only"
    unknown.mkdir()
    (unknown / "readme.txt").touch()

def run_test():
    with tempfile.TemporaryDirectory() as temp_dir:
        library_root = Path(temp_dir)
        logger.info(f"Created temp library at {library_root}")
        
        create_mock_library(library_root)
        
        logger.info(f"{'SERIES NAME':<40} | {'DETECTED MODE'}")
        logger.info("-" * 70)

        results = {}
        
        for series_folder in sorted(library_root.iterdir()):
            if series_folder.is_dir():
                mode = classify_series_structure(series_folder)
                logger.info(f"{series_folder.name:<40} | {mode}")
                results[series_folder.name] = mode
                
        # Assertions
        assert "Mode 1" in results["Berserk"]
        assert "Mode 2" in results["Batman"]
        assert "Mode 3" in results["Transferred to the Gyaru Academy"]
        assert "Empty Folder" in results["Empty Series"]
        assert "Unknown Structure" in results["Text Only"]
        
        logger.info("\nAll tests passed!")

if __name__ == "__main__":
    run_test()
