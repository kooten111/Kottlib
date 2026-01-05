
import json
import hashlib
import logging
import shutil
from pathlib import Path
from typing import Optional, Any, Dict
from ..database import get_data_dir

logger = logging.getLogger(__name__)

class LibraryCacheService:
    """
    Service to handle file-based caching for library browse responses.
    Caches separate JSON files for each browse path/query combination.
    """

    def __init__(self, library_id: int):
        self.library_id = library_id
        # Cache directory: data/cache/{id}/browse/
        # We use ID instead of name because name can change, ID is stable.
        self.cache_dir = get_data_dir() / "cache" / str(library_id) / "browse"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, path: str, params: Dict[str, Any]) -> str:
        """Generate a unique cache filename based on path and query parameters."""
        # Normalize params to ensure consistent ordering
        sorted_params = sorted([(k, str(v)) for k, v in params.items() if v is not None])
        raw_key = f"{path}|{sorted_params}"
        return hashlib.md5(raw_key.encode('utf-8')).hexdigest()

    def get_cached_response(self, path: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Retrieve cached JSON response if it exists."""
        if params is None:
            params = {}
            
        cache_key = self._get_cache_key(path, params)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {e}")
                return None
        return None

    def cache_response(self, path: str, data: Any, params: Dict[str, Any] = None) -> None:
        """Save JSON response to cache."""
        from fastapi.encoders import jsonable_encoder
        
        if params is None:
            params = {}

        cache_key = self._get_cache_key(path, params)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(jsonable_encoder(data), f)
        except Exception as e:
            logger.warning(f"Failed to write cache file {cache_file}: {e}")

    def invalidate_all(self) -> None:
        """Delete all cached files for this library."""
        if self.cache_dir.exists():
            try:
                shutil.rmtree(self.cache_dir)
                self._ensure_cache_dir()
                logger.info(f"Invalidated browse cache for library {self.library_id}")
            except Exception as e:
                logger.error(f"Failed to invalidate cache for library {self.library_id}: {e}")

# Factory function
def get_library_cache(library_id: int) -> LibraryCacheService:
    return LibraryCacheService(library_id)
