"""
Metadata Service

Handles applying scanner results to comics in the database.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import logging

# Add scanners to path
SCANNERS_PATH = Path(__file__).parent.parent.parent / "scanners"
sys.path.insert(0, str(SCANNERS_PATH))

from scanners.base_scanner import ScanResult, MatchConfidence
from scanners.metadata_schema import (
    map_scanner_metadata_to_comic,
    get_scanner_capabilities,
    FIELD_DEFINITIONS,
    MetadataField
)

from ..database.models import Comic

logger = logging.getLogger(__name__)


class MetadataApplicationResult:
    """Result of applying metadata to a comic"""
    def __init__(
        self,
        comic_id: int,
        success: bool,
        fields_updated: List[str],
        error: Optional[str] = None
    ):
        self.comic_id = comic_id
        self.success = success
        self.fields_updated = fields_updated
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comic_id": self.comic_id,
            "success": self.success,
            "fields_updated": self.fields_updated,
            "error": self.error
        }


class MetadataService:
    """Service for applying scanner metadata to comics"""

    @staticmethod
    def apply_scan_result_to_comic(
        session: Session,
        comic: Comic,
        scan_result: ScanResult,
        scanner_name: str,
        overwrite: bool = False,
        selected_fields: Optional[List[str]] = None
    ) -> MetadataApplicationResult:
        """
        Apply scan result metadata to a comic

        Args:
            session: Database session
            comic: Comic object to update
            scan_result: Scanner result with metadata
            scanner_name: Name of scanner that produced result
            overwrite: If True, overwrite existing metadata. If False, only fill empty fields.
            selected_fields: If provided, only apply these fields. Otherwise apply all.

        Returns:
            MetadataApplicationResult with update status
        """
        try:
            # Get scanner capabilities
            capabilities = get_scanner_capabilities(scanner_name)
            if not capabilities:
                logger.warning(f"No capabilities defined for scanner: {scanner_name}")

            # Map scanner metadata to comic fields
            comic_data = map_scanner_metadata_to_comic(scan_result.metadata)

            # Track updated fields
            fields_updated = []

            # Apply each field
            for db_column, value in comic_data.items():
                # Skip if field not in selection
                if selected_fields and db_column not in selected_fields:
                    continue

                # Get current value
                current_value = getattr(comic, db_column, None)

                # Decide whether to update
                should_update = False
                if overwrite:
                    # Always update if overwrite is enabled
                    should_update = True
                elif current_value is None or current_value == "":
                    # Update if field is empty
                    should_update = True

                if should_update:
                    setattr(comic, db_column, value)
                    fields_updated.append(db_column)
                    logger.debug(f"Updated {db_column}: {value}")

            # Also store source URL in web field if available
            if scan_result.source_url and (overwrite or not comic.web):
                if not selected_fields or 'web' in selected_fields:
                    comic.web = scan_result.source_url
                    fields_updated.append('web')

            # Commit changes
            session.commit()
            session.refresh(comic)

            logger.info(f"Applied metadata to comic {comic.id}: {len(fields_updated)} fields updated")

            return MetadataApplicationResult(
                comic_id=comic.id,
                success=True,
                fields_updated=fields_updated
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to apply metadata to comic {comic.id}: {e}")
            return MetadataApplicationResult(
                comic_id=comic.id,
                success=False,
                fields_updated=[],
                error=str(e)
            )

    @staticmethod
    def get_metadata_preview(
        comic: Comic,
        scan_result: ScanResult,
        scanner_name: str
    ) -> Dict[str, Any]:
        """
        Get a preview of what metadata would be applied

        Returns a dict showing current vs new values for each field
        """
        # Map scanner metadata
        comic_data = map_scanner_metadata_to_comic(scan_result.metadata)

        # Get scanner capabilities
        capabilities = get_scanner_capabilities(scanner_name)

        preview = {
            "comic_id": comic.id,
            "comic_filename": comic.filename,
            "scanner": scanner_name,
            "confidence": scan_result.confidence,
            "confidence_level": scan_result.confidence_level.name,
            "source_url": scan_result.source_url,
            "fields": []
        }

        # Compare each field
        for db_column, new_value in comic_data.items():
            current_value = getattr(comic, db_column, None)

            # Find field definition
            field_def = None
            for field_enum, definition in FIELD_DEFINITIONS.items():
                if definition.db_column == db_column:
                    field_def = definition
                    break

            field_info = {
                "field": db_column,
                "display_name": field_def.display_name if field_def else db_column,
                "current_value": current_value,
                "new_value": new_value,
                "will_change": current_value != new_value,
                "is_empty": current_value is None or current_value == "",
                "is_primary": capabilities.is_primary_field(field_def.field) if capabilities and field_def else False
            }

            preview["fields"].append(field_info)

        return preview

    @staticmethod
    def batch_apply_metadata(
        session: Session,
        comic_scan_pairs: List[Tuple[Comic, ScanResult, str]],
        overwrite: bool = False
    ) -> List[MetadataApplicationResult]:
        """
        Apply metadata to multiple comics at once

        Args:
            session: Database session
            comic_scan_pairs: List of (comic, scan_result, scanner_name) tuples
            overwrite: Whether to overwrite existing metadata

        Returns:
            List of application results
        """
        results = []

        for comic, scan_result, scanner_name in comic_scan_pairs:
            result = MetadataService.apply_scan_result_to_comic(
                session,
                comic,
                scan_result,
                scanner_name,
                overwrite=overwrite
            )
            results.append(result)

        return results

    @staticmethod
    def get_scanner_field_mapping(scanner_name: str) -> Dict[str, Any]:
        """
        Get information about what fields a scanner provides

        Returns a dict showing all fields the scanner can provide,
        organized by category.
        """
        capabilities = get_scanner_capabilities(scanner_name)
        if not capabilities:
            return {
                "scanner": scanner_name,
                "error": "Scanner capabilities not defined"
            }

        fields_by_category = {}

        for field in capabilities.provided_fields:
            field_def = FIELD_DEFINITIONS.get(field)
            if not field_def:
                continue

            category = field_def.category.value
            if category not in fields_by_category:
                fields_by_category[category] = []

            fields_by_category[category].append({
                "field": field.value,
                "display_name": field_def.display_name,
                "description": field_def.description,
                "db_column": field_def.db_column,
                "is_primary": capabilities.is_primary_field(field),
                "data_type": field_def.data_type
            })

        return {
            "scanner": scanner_name,
            "description": capabilities.description,
            "total_fields": len(capabilities.provided_fields),
            "primary_fields": len(capabilities.primary_fields),
            "fields_by_category": fields_by_category
        }
