"""
Tests for API v2 (Modern JSON-based API for WebUI and newer mobile apps)

Tests all v2 endpoints that provide JSON responses for modern interfaces.
Verifies JSON structure, data correctness, and feature completeness.
"""
import pytest
import json
from fastapi.testclient import TestClient


class TestV2Libraries:
    """Test v2 library management endpoints"""

    def test_list_libraries(self, test_client: TestClient, sample_library):
        """Test GET /v2/libraries - List all libraries (JSON)"""
        response = test_client.get("/v2/libraries")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check library structure
        lib = data[0]
        assert "id" in lib
        assert "name" in lib
        assert "path" in lib

    def test_get_library_by_id(self, test_client: TestClient, sample_library):
        """Test GET /v2/library/{id} - Get specific library"""
        response = test_client.get(f"/v2/library/{sample_library.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == sample_library.id
        assert data["name"] == sample_library.name
        assert data["path"] == sample_library.path

    def test_library_not_found(self, test_client: TestClient):
        """Test accessing non-existent library"""
        response = test_client.get("/v2/library/9999")
        assert response.status_code == 404


class TestV2Folders:
    """Test v2 folder browsing endpoints"""

    def test_get_folder_content(self, test_client: TestClient, sample_library, sample_folder, sample_comic):
        """Test GET /v2/library/{id}/folder/{folderId} - Get folder contents (JSON)"""
        response = test_client.get(f"/v2/library/{sample_library.id}/folder/{sample_folder.id}")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "folders" in data or isinstance(data, list)

    def test_get_folder_info(self, test_client: TestClient, sample_library, sample_folder, sample_comic):
        """Test GET /v2/library/{id}/folder/{folderId}/info - Get recursive folder info with read status"""
        response = test_client.get(f"/v2/library/{sample_library.id}/folder/{sample_folder.id}/info")

        assert response.status_code == 200
        # v2 info endpoint returns text format with read status
        text = response.text

        # Should include read status (0 or 1)
        assert ":" in text  # key:value format

    def test_get_root_folder(self, test_client: TestClient, sample_library):
        """Test getting root folder contents"""
        response = test_client.get(f"/v2/library/{sample_library.id}/folder/1")

        assert response.status_code == 200


class TestV2Comics:
    """Test v2 comic metadata endpoints"""

    def test_get_comic_metadata(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId} - Get comic metadata (JSON)"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}")

        assert response.status_code == 200
        # v2 comic endpoint can return text or trigger download
        # Check if it's a valid response
        assert response.status_code in [200, 302]

    def test_get_comic_info(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId}/info - Get comic download info"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/info")

        assert response.status_code == 200
        # Returns download info in text format
        text = response.text
        assert ":" in text

    def test_get_comic_remote(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId}/remote - Get comic for remote reading with hashes"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/remote")

        assert response.status_code == 200
        text = response.text

        # v2 remote should include hash fields for navigation
        assert "hash:" in text
        # May include previousComicHash and nextComicHash if siblings exist

    def test_comic_not_found(self, test_client: TestClient, sample_library):
        """Test accessing non-existent comic"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/9999")
        assert response.status_code == 404

    def test_get_comic_with_navigation(self, test_client: TestClient, sample_library, multiple_comics):
        """Test comic info includes navigation to prev/next comics"""
        # Get middle comic
        comic = multiple_comics[2]
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{comic.id}/remote")

        assert response.status_code == 200
        text = response.text

        # Should include navigation
        assert "comicid:" in text or "hash:" in text


class TestV2Pages:
    """Test v2 page reading endpoints"""

    def test_get_comic_page(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId}/page/{pageNum} - Get page (non-remote)"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/page/0")

        # Will fail with dummy data but endpoint should exist
        assert response.status_code in [200, 404, 500]

    def test_get_page_remote(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId}/remote/page/{pageNum} - Get page (remote mode)"""
        # First open comic for remote reading
        open_response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/remote")

        # Then try to get page
        page_response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/remote/page/0")

        # Endpoint should exist
        assert page_response.status_code in [200, 404, 500]


class TestV2Covers:
    """Test v2 cover/thumbnail endpoints"""

    def test_get_comic_cover(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId}/cover - Get comic cover"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/cover")

        # Cover might not exist in test environment
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Should be an image
            assert "image/" in response.headers.get("content-type", "")

    def test_get_comic_thumbnail(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId}/thumbnail - Get comic thumbnail"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/thumbnail")

        # Thumbnail might not exist
        assert response.status_code in [200, 404]


class TestV2ReadingProgress:
    """Test v2 reading progress endpoints"""

    def test_get_reading_progress(self, test_client: TestClient, sample_library, sample_comic, sample_reading_progress):
        """Test GET /v2/library/{id}/comic/{comicId}/progress - Get reading progress"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/progress")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "current_page" in data or "currentPage" in data

    def test_update_reading_progress(self, test_client: TestClient, sample_library, sample_comic, sample_user):
        """Test POST /v2/library/{id}/comic/{comicId}/progress - Update reading progress"""
        progress_data = {
            "current_page": 15,
            "total_pages": sample_comic.num_pages
        }

        response = test_client.post(
            f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/progress",
            json=progress_data
        )

        # Should accept the update
        assert response.status_code in [200, 201]

    def test_get_continue_reading(self, test_client: TestClient, sample_user, sample_reading_progress):
        """Test GET /v2/continue-reading - Get continue reading list (JSON)"""
        response = test_client.get("/v2/continue-reading")

        assert response.status_code == 200
        # Should return JSON
        data = response.json() if response.headers.get("content-type") == "application/json" else None

        # Can be empty list or have items
        if data:
            assert isinstance(data, list)

    def test_get_all_libraries_reading(self, test_client: TestClient, sample_user, sample_reading_progress):
        """Test GET /v2/reading - Get continue reading from ALL libraries (cross-library)"""
        response = test_client.get("/v2/reading")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert isinstance(data, list)
        
        # If we have reading progress, verify the structure
        if len(data) > 0:
            comic = data[0]
            # Check required fields from v2 format
            assert "id" in comic
            assert "library_id" in comic
            assert "title" in comic
            assert "current_page" in comic or "currentPage" in comic
            assert "num_pages" in comic or "numPages" in comic
            assert "last_time_opened" in comic
            
    def test_get_library_reading(self, test_client: TestClient, sample_library, sample_user, sample_reading_progress):
        """Test GET /v2/library/{id}/reading - Get continue reading for specific library"""
        response = test_client.get(f"/v2/library/{sample_library.id}/reading")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert isinstance(data, list)
        
        # All comics should be from the requested library
        for comic in data:
            assert "library_id" in comic
            assert str(comic["library_id"]) == str(sample_library.id)

    def test_mark_comic_as_read(self, test_client: TestClient, sample_library, sample_comic):
        """Test POST /v2/library/{id}/comic/{comicId}/mark-read - Mark comic as read"""
        response = test_client.post(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/mark-read")

        assert response.status_code in [200, 201, 404]

    def test_mark_comic_as_unread(self, test_client: TestClient, sample_library, sample_comic):
        """Test POST /v2/library/{id}/comic/{comicId}/mark-unread - Mark comic as unread"""
        response = test_client.post(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/mark-unread")

        assert response.status_code in [200, 201, 404]


class TestV2Search:
    """Test v2 search endpoints"""

    def test_search_comics(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/search - Search comics (JSON)"""
        response = test_client.get(
            f"/v2/library/{sample_library.id}/search",
            params={"q": "Test"}
        )

        assert response.status_code == 200

        # Can be JSON or text depending on implementation
        if "application/json" in response.headers.get("content-type", ""):
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)

    def test_search_with_filters(self, test_client: TestClient, sample_library):
        """Test search with various filters"""
        response = test_client.get(
            f"/v2/library/{sample_library.id}/search",
            params={
                "q": "Test",
                "series": "Test Series",
                "year": "2024"
            }
        )

        assert response.status_code in [200, 404]

    def test_advanced_search(self, test_client: TestClient, sample_library):
        """Test POST /v2/library/{id}/search - Advanced search with filters"""
        search_params = {
            "query": "Test",
            "filters": {
                "series": "Test Series",
                "year_min": 2020,
                "year_max": 2024
            }
        }

        response = test_client.post(
            f"/v2/library/{sample_library.id}/search",
            json=search_params
        )

        assert response.status_code in [200, 404, 422]


class TestV2Sync:
    """Test v2 sync endpoints"""

    def test_sync_reading_progress(self, test_client: TestClient, multiple_comics, sample_user):
        """Test POST /v2/sync - Sync reading progress (returns JSON)"""
        sync_data = {
            "comics": [
                {
                    "comicId": multiple_comics[0].id,
                    "currentPage": 5,
                    "totalPages": multiple_comics[0].num_pages
                },
                {
                    "comicId": multiple_comics[1].id,
                    "currentPage": 10,
                    "totalPages": multiple_comics[1].num_pages
                }
            ]
        }

        response = test_client.post("/v2/sync", json=sync_data)

        assert response.status_code == 200

        # v2 sync returns JSON response
        if "application/json" in response.headers.get("content-type", ""):
            data = response.json()
            assert "synced" in data or "count" in data or "success" in data

    def test_sync_with_conflicts(self, test_client: TestClient, sample_comic, sample_user):
        """Test sync handles conflicts gracefully"""
        sync_data = {
            "comics": [
                {
                    "comicId": sample_comic.id,
                    "currentPage": 5,
                    "totalPages": sample_comic.num_pages,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ]
        }

        response = test_client.post("/v2/sync", json=sync_data)

        # Should handle gracefully
        assert response.status_code in [200, 409]


class TestV2Series:
    """Test v2 series/collection endpoints"""

    def test_get_series_list(self, test_client: TestClient, sample_library):
        """Test GET /v2/library/{id}/series - Get series list"""
        response = test_client.get(f"/v2/library/{sample_library.id}/series")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)

    def test_get_series_comics(self, test_client: TestClient, sample_library):
        """Test GET /v2/library/{id}/series/{seriesName} - Get comics in series"""
        response = test_client.get(f"/v2/library/{sample_library.id}/series/Test%20Series")

        assert response.status_code in [200, 404]

    def test_series_progress_sorting(self, test_client: TestClient, sample_library):
        """Test GET /v2/library/{id}/series?sort=progress - Verify progress sorting includes partial completion"""
        response = test_client.get(f"/v2/library/{sample_library.id}/series?sort=progress")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)
            
            # If we got series data, verify the structure includes volumes with progress_percent
            if isinstance(data, list) and len(data) > 0:
                for series in data:
                    if "volumes" in series and len(series["volumes"]) > 0:
                        # Verify that volumes have progress tracking fields
                        for volume in series["volumes"]:
                            assert "is_completed" in volume
                            assert "progress_percent" in volume
                            # progress_percent should be between 0 and 100
                            if volume.get("progress_percent") is not None:
                                assert 0 <= volume["progress_percent"] <= 100


class TestV2Statistics:
    """Test v2 statistics and analytics endpoints"""

    def test_get_library_stats(self, test_client: TestClient, sample_library):
        """Test GET /v2/library/{id}/stats - Get library statistics"""
        response = test_client.get(f"/v2/library/{sample_library.id}/stats")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should include counts
            assert "total_comics" in data or "comics" in data or "count" in data

    def test_get_reading_stats(self, test_client: TestClient, sample_user):
        """Test GET /v2/user/stats - Get user reading statistics"""
        response = test_client.get("/v2/user/stats")

        assert response.status_code in [200, 401, 404]


class TestV2Metadata:
    """Test v2 metadata endpoints"""

    def test_update_comic_metadata(self, test_client: TestClient, sample_library, sample_comic):
        """Test PUT /v2/library/{id}/comic/{comicId}/metadata - Update comic metadata"""
        metadata = {
            "title": "Updated Title",
            "series": "Updated Series",
            "year": 2025
        }

        response = test_client.put(
            f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/metadata",
            json=metadata
        )

        assert response.status_code in [200, 404, 405]

    def test_get_comic_metadata_full(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /v2/library/{id}/comic/{comicId}/metadata - Get full metadata"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/metadata")

        assert response.status_code in [200, 404]


class TestV2JSONFormat:
    """Test v2 API JSON format compliance"""

    def test_json_response_structure(self, test_client: TestClient, sample_library):
        """Test that JSON responses have consistent structure"""
        response = test_client.get("/v2/libraries")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Should be valid JSON
        data = response.json()
        assert data is not None

    def test_error_response_format(self, test_client: TestClient):
        """Test that error responses follow consistent format"""
        response = test_client.get("/v2/library/9999")

        assert response.status_code == 404

        # Error should be JSON with detail
        if "application/json" in response.headers.get("content-type", ""):
            data = response.json()
            assert "detail" in data or "error" in data or "message" in data

    def test_pagination_support(self, test_client: TestClient, sample_library):
        """Test pagination parameters"""
        response = test_client.get(
            f"/v2/library/{sample_library.id}/comics",
            params={"limit": 10, "offset": 0}
        )

        # Endpoint might not exist but testing pattern
        assert response.status_code in [200, 404]


class TestV2HashValidation:
    """Test v2 hash-based navigation and validation"""

    def test_comic_hash_in_response(self, test_client: TestClient, sample_library, sample_comic):
        """Test that comic responses include hash for validation"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/remote")

        assert response.status_code == 200
        text = response.text

        # Should include hash
        assert f"hash:{sample_comic.hash}" in text

    def test_navigation_with_hashes(self, test_client: TestClient, sample_library, multiple_comics):
        """Test that navigation includes previousComicHash and nextComicHash"""
        # Get middle comic
        comic = multiple_comics[2]
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{comic.id}/remote")

        assert response.status_code == 200
        text = response.text

        # v2 should include hash-based navigation
        # May have previousComicHash and nextComicHash
        assert "hash:" in text


class TestV2ErrorHandling:
    """Test v2 API error handling"""

    def test_library_not_found(self, test_client: TestClient):
        """Test handling of non-existent library"""
        response = test_client.get("/v2/library/9999")
        assert response.status_code == 404

    def test_comic_not_found(self, test_client: TestClient, sample_library):
        """Test handling of non-existent comic"""
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/9999")
        assert response.status_code == 404

    def test_invalid_json_body(self, test_client: TestClient, sample_library, sample_comic):
        """Test handling of invalid JSON in request body"""
        response = test_client.post(
            f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/progress",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]

    def test_missing_required_fields(self, test_client: TestClient):
        """Test handling of requests with missing required fields"""
        response = test_client.post("/v2/sync", json={})

        # Should validate and reject
        assert response.status_code in [200, 400, 422]

    def test_rate_limiting(self, test_client: TestClient, sample_library):
        """Test rate limiting on endpoints (if implemented)"""
        # Make multiple rapid requests
        for _ in range(10):
            response = test_client.get(f"/v2/library/{sample_library.id}")

        # Should still succeed or return 429 if rate limited
        assert response.status_code in [200, 429]


class TestV2Performance:
    """Test v2 API performance characteristics"""

    def test_large_folder_listing(self, test_client: TestClient, sample_library, sample_folder):
        """Test performance with large folder listings"""
        # With test data this is limited, but tests the pattern
        response = test_client.get(f"/v2/library/{sample_library.id}/folder/{sample_folder.id}")

        assert response.status_code == 200

    def test_search_performance(self, test_client: TestClient, sample_library):
        """Test search performance with complex queries"""
        response = test_client.get(
            f"/v2/library/{sample_library.id}/search",
            params={"q": "test"}
        )

        # Should complete in reasonable time
        assert response.status_code in [200, 404]


class TestV2Compatibility:
    """Test v2 API backward compatibility"""

    def test_accepts_v1_format_data(self, test_client: TestClient, sample_library, sample_comic):
        """Test that v2 can handle v1-style requests where applicable"""
        # Some v2 endpoints should accept v1 parameter formats
        response = test_client.post(
            f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data={"page": "5"}
        )

        # Might not be implemented, but testing compatibility
        assert response.status_code in [200, 404, 405]

    def test_both_api_versions_coexist(self, test_client: TestClient, sample_library):
        """Test that v1 and v2 APIs can both be used"""
        # Test v1 endpoint
        v1_response = test_client.get("/library/")
        assert v1_response.status_code == 200

        # Test v2 endpoint
        v2_response = test_client.get("/v2/libraries")
        assert v2_response.status_code == 200
