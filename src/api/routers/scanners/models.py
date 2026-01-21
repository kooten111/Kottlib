"""
Pydantic models for scanner API endpoints.

Contains all request/response models used by the scanner router.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class ScanLevelEnum(str, Enum):
    """Scan level enumeration."""
    FILE = "file"
    SERIES = "series"


class ConfidenceLevelEnum(str, Enum):
    """Confidence level enumeration."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXACT = "EXACT"


# ============================================================================
# Scanner Info Models
# ============================================================================

class ScanResultModel(BaseModel):
    """Scan result response model."""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    confidence_level: ConfidenceLevelEnum
    source_id: Optional[str] = Field(None, description="ID from external source")
    source_url: Optional[str] = Field(None, description="URL to source")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "confidence": 1.0,
                "confidence_level": "EXACT",
                "source_id": "573470",
                "source_url": "https://nhentai.net/g/573470",
                "metadata": {
                    "title": "(C102) [Yachan Coffee] ...",
                    "artists": ["yachan"],
                    "groups": ["yachan coffee"]
                },
                "tags": ["tag:swimsuit", "artist:yachan"]
            }
        }


class ScannerInfo(BaseModel):
    """Information about an available scanner."""
    name: str
    scan_level: ScanLevelEnum
    description: Optional[str] = None
    requires_config: bool = False
    config_keys: List[str] = Field(default_factory=list)  # DEPRECATED: use config_schema instead
    config_schema: List[Dict[str, Any]] = Field(default_factory=list)  # Declarative config schema
    provided_fields: List[str] = Field(default_factory=list)
    primary_fields: List[str] = Field(default_factory=list)


# ============================================================================
# Library Scanner Configuration Models
# ============================================================================

class LibraryScannerConfig(BaseModel):
    """Scanner configuration for a library."""
    library_id: int
    library_name: str
    library_path: Optional[str] = None
    primary_scanner: Optional[str] = None
    scan_level: Optional[ScanLevelEnum] = None  # FILE or SERIES - determines UI scanning options
    fallback_scanners: List[str] = Field(default_factory=list)
    fallback_threshold: float = Field(0.7, ge=0.0, le=1.0)
    confidence_threshold: float = Field(0.4, ge=0.0, le=1.0)
    scanner_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class UpdateLibraryScannerConfig(BaseModel):
    """Request model for updating library scanner configuration."""
    primary_scanner: str = Field(..., description="Primary scanner to use")
    fallback_scanners: List[str] = Field(default_factory=list, description="Fallback scanners (optional)")
    confidence_threshold: float = Field(0.4, ge=0.0, le=1.0, description="Minimum confidence threshold")
    fallback_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Threshold to trigger fallback")
    scanner_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Configuration for specific scanners (e.g. API keys)")

    class Config:
        json_schema_extra = {
            "example": {
                "primary_scanner": "nhentai",
                "fallback_scanners": [],
                "confidence_threshold": 0.4,
                "fallback_threshold": 0.7
            }
        }


# ============================================================================
# Scan Request/Response Models
# ============================================================================

class ScanRequest(BaseModel):
    """Request to scan a file or series."""
    query: str = Field(..., description="Filename or series name to scan")
    library_id: Optional[int] = Field(None, description="Library ID (recommended)")
    scanner_name: Optional[str] = Field(None, description="Specific scanner to use (overrides library config)")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    # Deprecated fields for backward compatibility
    library_type: Optional[str] = Field(None, description="[DEPRECATED] Use library_id instead")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "[Artist] Comic Title [English].cbz",
                "library_id": 1,
                "confidence_threshold": 0.4
            }
        }


class BulkScanRequest(BaseModel):
    """Request to scan multiple files."""
    queries: List[str] = Field(..., description="List of filenames or series names")
    library_id: int = Field(..., description="Library ID")
    confidence_threshold: Optional[float] = Field(0.4, ge=0.0, le=1.0)
    # Deprecated field
    library_type: Optional[str] = Field(None, description="[DEPRECATED] Use library_id instead")


class BulkScanResult(BaseModel):
    """Result of bulk scan operation."""
    total: int
    matched: int
    rejected: int
    results: List[Dict[str, Any]]


# ============================================================================
# Comic/Library Scanning Models
# ============================================================================

class ScanComicRequest(BaseModel):
    """Request model for scanning a comic."""
    comic_id: int
    overwrite: bool = Field(False, description="Overwrite existing metadata")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class ScanLibraryRequest(BaseModel):
    """Request model for scanning a library."""
    library_id: int
    overwrite: bool = Field(False, description="Overwrite existing metadata")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    rescan_existing: bool = Field(False, description="Rescan comics already scanned")


class ClearMetadataRequest(BaseModel):
    """Request model for clearing metadata."""
    comic_ids: Optional[List[int]] = Field(None, description="Specific comic IDs to clear")
    library_id: Optional[int] = Field(None, description="Clear all comics in library")
    clear_scanner_info: bool = Field(True, description="Clear scanner metadata")
    clear_tags: bool = Field(True, description="Clear tags")
    clear_metadata: bool = Field(False, description="Clear all metadata fields")


class ScanComicResponse(BaseModel):
    """Response for comic scan."""
    comic_id: int
    success: bool
    confidence: Optional[float] = None
    fields_updated: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    candidates: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of candidate matches for manual selection")


class ScanLibraryResponse(BaseModel):
    """Response for library scan."""
    total_comics: int
    scanned: int
    failed: int
    skipped: int
    results: List[ScanComicResponse]


class ApplySeriesMetadataRequest(BaseModel):
    """Request model for applying manually selected metadata to a series."""
    library_id: int
    series_name: str
    source_id: str
    source_url: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    overwrite: bool = Field(False, description="Overwrite existing metadata")


class ApplyComicMetadataRequest(BaseModel):
    """Request model for applying manually selected metadata to a comic."""
    comic_id: int
    source_id: str
    source_url: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    overwrite: bool = Field(False, description="Overwrite existing metadata")
