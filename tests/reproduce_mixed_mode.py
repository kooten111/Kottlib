import shutil
from pathlib import Path
import sys
from unittest.mock import MagicMock

# Mock rarfile before importing scanner
sys.modules['rarfile'] = MagicMock()
sys.modules['py7zr'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scanner.threaded_scanner import ThreadedScanner

def test_mixed_mode_detection():
    """
    Test that a folder with both files and subfolders (Mixed Mode)
    is correctly identified as Nested/Franchise, not Simple.
    """
    base_path = Path("/tmp/test_mixed_mode_library")
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)

    # Create Mixed Mode structure (DnD case)
    # Root/DnD/
    #   - file.cbr
    #   - Subfolder/
    #       - file2.cbr
    
    dnd_path = base_path / "DnD"
    dnd_path.mkdir()
    
    # Direct file
    (dnd_path / "Shadows of the Vampire.cbr").touch()
    
    # Subfolder with file
    subfolder = dnd_path / "Evil at Baldurs Gate"
    subfolder.mkdir()
    (subfolder / "Issue 1.cbr").touch()

    # Initialize scanner (mock DB)
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    
    scanner = ThreadedScanner(mock_db, 1)
    
    # Test classification
    mode = scanner._classify_series_structure(dnd_path)
    print(f"DnD Structure Mode: {mode}")
    
    # Assertions
    # Current buggy behavior: returns "simple" because of the direct file
    # Desired behavior: returns "nested" (or "mixed") because of the subfolder
    
    if mode == "simple":
        print("FAIL: Detected as 'simple' (Current Bug)")
    elif mode == "nested":
        print("SUCCESS: Detected as 'nested'")
    else:
        print(f"Unexpected mode: {mode}")

    # Cleanup
    shutil.rmtree(base_path)

if __name__ == "__main__":
    test_mixed_mode_detection()
