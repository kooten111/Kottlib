"""
Test metadata service functionality.
"""
import pytest
from unittest.mock import MagicMock

from src.services.metadata_service import (
    MetadataService,
    MetadataApplicationResult,
)
from src.metadata_providers.base import ScanResult, MatchConfidence
from src.database.models import Comic


class TestMetadataApplicationResult:
    """Test MetadataApplicationResult data class"""
    
    def test_create_success_result(self):
        """Test creating a successful result"""
        result = MetadataApplicationResult(
            comic_id=1,
            success=True,
            fields_updated=['title', 'series', 'year']
        )
        
        assert result.comic_id == 1
        assert result.success is True
        assert len(result.fields_updated) == 3
        assert result.error is None
    
    def test_create_error_result(self):
        """Test creating an error result"""
        result = MetadataApplicationResult(
            comic_id=1,
            success=False,
            fields_updated=[],
            error="Test error message"
        )
        
        assert result.comic_id == 1
        assert result.success is False
        assert len(result.fields_updated) == 0
        assert result.error == "Test error message"
    
    def test_to_dict(self):
        """Test converting result to dictionary"""
        result = MetadataApplicationResult(
            comic_id=1,
            success=True,
            fields_updated=['title']
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['comic_id'] == 1
        assert result_dict['success'] is True
        assert 'title' in result_dict['fields_updated']
        assert result_dict['error'] is None


class TestApplyScanResultToComic:
    """Test applying scan results to comics"""
    
    def test_apply_basic_metadata(self, test_db, sample_comic):
        """Test applying basic metadata to a comic"""
        scan_result = ScanResult(
            confidence=0.95,
            source_id="12345",
            source_url="https://example.com/12345",
            metadata={
                'title': 'New Title',
                'summary': 'New summary',
                'year': 2024,
                'artists': ['Artist 1', 'Artist 2']
            },
            tags=['tag1', 'tag2']
        )
        
        with test_db.get_session() as session:
            comic = session.query(Comic).filter_by(id=sample_comic.id).first()
            
            result = MetadataService.apply_scan_result_to_comic(
                session=session,
                comic=comic,
                scan_result=scan_result,
                scanner_name='test_scanner',
                overwrite=True
            )
            
            assert result.success is True
            assert len(result.fields_updated) > 0
            
            # Refresh comic to see changes
            session.refresh(comic)
            assert comic.title == 'New Title'
            assert comic.summary == 'New summary'
            assert comic.year == 2024
    
    def test_apply_metadata_no_overwrite(self, test_db, sample_comic):
        """Test applying metadata without overwriting existing fields"""
        # Sample comic already has title
        scan_result = ScanResult(
            confidence=0.90,
            source_id="12345",
            source_url="https://example.com/12345",
            metadata={
                'title': 'Should Not Overwrite',
                'summary': 'New summary'  # This field is empty, should update
            },
            tags=[]
        )
        
        with test_db.get_session() as session:
            comic = session.query(Comic).filter_by(id=sample_comic.id).first()
            original_title = comic.title
            
            result = MetadataService.apply_scan_result_to_comic(
                session=session,
                comic=comic,
                scan_result=scan_result,
                scanner_name='test_scanner',
                overwrite=False  # Don't overwrite existing fields
            )
            
            session.refresh(comic)
            assert comic.title == original_title  # Title should not change
            assert comic.summary == 'New summary'  # Empty field should be filled
    
    def test_apply_metadata_with_selected_fields(self, test_db, sample_comic):
        """Test applying only selected metadata fields"""
        scan_result = ScanResult(
            confidence=0.85,
            source_id="12345",
            source_url="https://example.com/12345",
            metadata={
                'title': 'New Title',
                'summary': 'New Summary',
                'year': 2024,
                'publisher': 'New Publisher'
            },
            tags=[]
        )
        
        with test_db.get_session() as session:
            comic = session.query(Comic).filter_by(id=sample_comic.id).first()
            
            result = MetadataService.apply_scan_result_to_comic(
                session=session,
                comic=comic,
                scan_result=scan_result,
                scanner_name='test_scanner',
                overwrite=True,
                selected_fields=['title', 'year']  # Only apply these fields
            )
            
            session.refresh(comic)
            assert comic.title == 'New Title'
            assert comic.year == 2024
            # Summary and publisher should not be updated
            assert 'summary' not in result.fields_updated
            assert 'publisher' not in result.fields_updated
    
    def test_apply_metadata_stores_scanner_info(self, test_db, sample_comic):
        """Test that scanner metadata is stored"""
        scan_result = ScanResult(
            confidence=0.92,
            source_id="scan123",
            source_url="https://scanner.com/scan123",
            metadata={'title': 'Scanned Title'},
            tags=['tag1']
        )
        
        with test_db.get_session() as session:
            comic = session.query(Comic).filter_by(id=sample_comic.id).first()
            
            result = MetadataService.apply_scan_result_to_comic(
                session=session,
                comic=comic,
                scan_result=scan_result,
                scanner_name='my_scanner',
                overwrite=True
            )
            
            session.refresh(comic)
            assert comic.scanner_source == 'my_scanner'
            assert comic.scanner_source_id == 'scan123'
            assert comic.scanner_source_url == 'https://scanner.com/scan123'
            assert comic.scan_confidence == 0.92
            assert comic.scanned_at is not None


class TestGetMetadataPreview:
    """Test metadata preview functionality"""
    
    def test_preview_shows_changes(self, test_db, sample_comic):
        """Test that preview correctly shows what would change"""
        scan_result = ScanResult(
            confidence=0.88,
            source_id="preview123",
            source_url="https://example.com/preview123",
            metadata={
                'title': 'New Title',
                'year': 2025
            },
            tags=['preview']
        )
        
        with test_db.get_session() as session:
            comic = session.query(Comic).filter_by(id=sample_comic.id).first()
            
            preview = MetadataService.get_metadata_preview(
                comic=comic,
                scan_result=scan_result,
                scanner_name='test_scanner'
            )
            
            assert preview['comic_id'] == sample_comic.id
            assert preview['scanner'] == 'test_scanner'
            assert preview['confidence'] == 0.88
            assert len(preview['fields']) > 0
            
            # Check that fields show current vs new values
            for field in preview['fields']:
                assert 'current_value' in field
                assert 'new_value' in field
                assert 'will_change' in field


class TestBatchApplyMetadata:
    """Test batch metadata application"""
    
    def test_batch_apply_multiple_comics(self, test_db, multiple_comics):
        """Test applying metadata to multiple comics at once"""
        # Create scan results for each comic
        comic_scan_pairs = []
        
        with test_db.get_session() as session:
            for i, comic in enumerate(multiple_comics):
                db_comic = session.query(Comic).filter_by(id=comic.id).first()
                scan_result = ScanResult(
                    confidence=0.90,
                    source_id=f"batch_{i}",
                    source_url=f"https://example.com/batch_{i}",
                    metadata={
                        'title': f'Batch Title {i}',
                        'year': 2024
                    },
                    tags=[]
                )
                comic_scan_pairs.append((db_comic, scan_result, 'batch_scanner'))
            
            results = MetadataService.batch_apply_metadata(
                session=session,
                comic_scan_pairs=comic_scan_pairs,
                overwrite=True
            )
            
            assert len(results) == len(multiple_comics)
            assert all(result.success for result in results)


class TestScannerFieldMapping:
    """Test scanner field mapping functionality"""
    
    def test_get_scanner_field_mapping(self):
        """Test retrieving scanner field mapping information"""
        # This test assumes a scanner is configured
        # In real implementation, you'd need to have scanners registered
        
        mapping = MetadataService.get_scanner_field_mapping('nhentai')
        
        # Should return scanner information
        assert 'scanner' in mapping
        
        # If scanner exists, should have fields
        if 'fields_by_category' in mapping:
            assert isinstance(mapping['fields_by_category'], dict)
    
    def test_get_field_mapping_unknown_scanner(self):
        """Test field mapping for unknown scanner"""
        mapping = MetadataService.get_scanner_field_mapping('unknown_scanner')
        
        assert 'scanner' in mapping
        # Should indicate error or empty mapping
        assert 'error' in mapping or 'fields_by_category' in mapping
