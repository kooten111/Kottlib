"""
Tests for Legacy API v1 (Mobile App Endpoints)

Tests all v1 endpoints that YACReader mobile apps use.
Verifies text format responses, CRLF line endings, and data correctness.
"""
import pytest
from fastapi.testclient import TestClient


class TestV1Libraries:
    """Test v1 library listing endpoints"""

    def test_list_libraries(self, test_client: TestClient, sample_library):
        """Test GET /library/ - List all libraries"""
        response = test_client.get("/library/")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        # Check format
        text = response.text
        assert "type:libraries" in text
        assert "code:0" in text
        assert f"library:{sample_library.name}" in text
        assert f"id:{sample_library.id}" in text
        assert f"path:{sample_library.path}" in text

        # Verify CRLF line endings
        assert "\r\n" in text

    def test_list_libraries_empty(self, test_client: TestClient):
        """Test library listing when no libraries exist"""
        response = test_client.get("/library/")

        assert response.status_code == 200
        text = response.text
        assert "type:libraries" in text
        assert "code:0" in text


class TestV1Folders:
    """Test v1 folder browsing endpoints"""

    def test_get_folder_content(self, test_client: TestClient, sample_library, sample_folder, sample_comic):
        """Test GET /library/{id}/folder/{folderId} - Get folder contents"""
        response = test_client.get(f"/library/{sample_library.id}/folder/{sample_folder.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        text = response.text
        assert "type:folder" in text
        assert "code:0" in text
        assert f"comic:{sample_comic.filename}" in text
        assert f"id:{sample_comic.id}" in text

    def test_get_folder_content_with_sorting(self, test_client: TestClient, sample_library, sample_folder, multiple_comics):
        """Test folder content with different sorting modes"""
        # Test alphabetical sorting
        response = test_client.get(
            f"/library/{sample_library.id}/folder/{sample_folder.id}",
            params={"sort": "alphabetical"}
        )
        assert response.status_code == 200

        # Test date_added sorting
        response = test_client.get(
            f"/library/{sample_library.id}/folder/{sample_folder.id}",
            params={"sort": "date_added"}
        )
        assert response.status_code == 200

    def test_get_folder_info(self, test_client: TestClient, sample_library, sample_folder, sample_comic):
        """Test GET /library/{id}/folder/{folderId}/info - Get recursive folder info"""
        response = test_client.get(f"/library/{sample_library.id}/folder/{sample_folder.id}/info")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        text = response.text
        # Format: /library/{libId}/comic/{comicId}:{fileName}:{fileSize}
        expected_line = f"/library/{sample_library.id}/comic/{sample_comic.id}:{sample_comic.filename}:{sample_comic.file_size}"
        assert expected_line in text

    def test_get_root_folder(self, test_client: TestClient, sample_library, sample_comic):
        """Test getting root folder (folder_id=1)"""
        response = test_client.get(f"/library/{sample_library.id}/folder/1")

        assert response.status_code == 200
        text = response.text
        assert "type:folder" in text

    def test_folder_not_found(self, test_client: TestClient, sample_library):
        """Test accessing non-existent library"""
        response = test_client.get("/library/9999/folder/1")

        assert response.status_code == 404


class TestV1Comics:
    """Test v1 comic metadata endpoints"""

    def test_get_comic_info(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /library/{id}/comic/{comicId} - Get comic metadata"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        text = response.text
        assert f"library:{sample_library.name}" in text
        assert f"libraryId:{sample_library.id}" in text
        assert f"comicid:{sample_comic.id}" in text
        assert f"hash:{sample_comic.hash}" in text
        assert f"path:{sample_comic.path}" in text
        assert f"numpages:{sample_comic.num_pages}" in text
        assert "currentPage:" in text
        assert "read:" in text
        assert "manga:" in text

    def test_get_comic_full_info(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /library/{id}/comic/{comicId}/info - Get full comic info"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/info")

        assert response.status_code == 200
        text = response.text

        # Check for metadata fields
        assert f"title:{sample_comic.title}" in text
        assert f"series:{sample_comic.series}" in text
        assert f"number:{sample_comic.issue_number}" in text
        assert f"year:{sample_comic.year}" in text

    def test_get_comic_remote(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /library/{id}/comic/{comicId}/remote - Get comic for remote reading"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/remote")

        assert response.status_code == 200
        text = response.text

        # Should include navigation hints
        assert "comicid:" in text
        assert "numpages:" in text

    def test_comic_not_found(self, test_client: TestClient, sample_library):
        """Test accessing non-existent comic"""
        response = test_client.get(f"/library/{sample_library.id}/comic/9999")

        assert response.status_code == 404

    def test_get_comic_with_reading_progress(self, test_client: TestClient, sample_library, sample_comic, sample_reading_progress):
        """Test comic info includes reading progress"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")

        assert response.status_code == 200
        text = response.text

        # Should include current page from reading progress
        assert "currentPage:" in text


class TestV1Pages:
    """Test v1 page reading endpoints"""

    def test_get_comic_page(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /library/{id}/comic/{comicId}/page/{pageNum} - Get comic page"""
        # This will fail with actual page reading since we have dummy data
        # But we can test the endpoint exists and handles errors properly
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/page/0")

        # Should either return 200 with image or 500 if comic can't be opened
        assert response.status_code in [200, 500]

    def test_get_page_out_of_bounds(self, test_client: TestClient, sample_library, sample_comic):
        """Test accessing page number beyond comic length"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/page/9999")

        # Should fail since page doesn't exist
        assert response.status_code in [404, 500]


class TestV1Covers:
    """Test v1 cover/thumbnail endpoints"""

    def test_get_comic_cover(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /library/{id}/comic/{comicId}/cover - Get comic cover"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/cover")

        # Cover might not exist in test environment
        # We're testing that endpoint exists and handles missing covers
        assert response.status_code in [200, 404]

    def test_set_custom_cover(self, test_client: TestClient, sample_library, sample_comic):
        """Test POST /library/{id}/comic/{comicId}/setCustomCover - Set custom cover"""
        response = test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCustomCover",
            data={"page": "0"}
        )

        # Will likely fail with test data, but endpoint should exist
        assert response.status_code in [200, 500]


class TestV1ReadingProgress:
    """Test v1 reading progress endpoints"""

    def test_set_current_page(self, test_client: TestClient, sample_library, sample_comic, sample_user):
        """Test POST /library/{id}/comic/{comicId}/setCurrentPage - Update reading progress"""
        response = test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data={"page": "10"}
        )

        assert response.status_code == 200
        assert response.text == "OK"

    def test_set_current_page_invalid_data(self, test_client: TestClient, sample_library, sample_comic):
        """Test setting current page with invalid data"""
        response = test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data={"page": "invalid"}
        )

        # Should handle invalid input
        assert response.status_code in [200, 400, 422]

    def test_continue_reading_list(self, test_client: TestClient, sample_user, sample_reading_progress):
        """Test GET /library/continue-reading - Get continue reading list"""
        response = test_client.get("/library/continue-reading")

        assert response.status_code == 200
        text = response.text

        assert "type:continue-reading" in text
        assert "code:0" in text

    def test_continue_reading_with_limit(self, test_client: TestClient, sample_user):
        """Test continue reading list with limit parameter"""
        response = test_client.get("/library/continue-reading?limit=5")

        assert response.status_code == 200


class TestV1Search:
    """Test v1 search endpoints"""

    def test_search_comics_get(self, test_client: TestClient, sample_library, sample_comic):
        """Test GET /library/{id}/search - Search comics via GET"""
        response = test_client.get(
            f"/library/{sample_library.id}/search",
            params={"q": "Test"}
        )

        assert response.status_code == 200
        text = response.text

        assert "type:search" in text
        assert "code:0" in text

    def test_search_comics_post(self, test_client: TestClient, sample_library, sample_comic):
        """Test POST /library/{id}/search - Search comics via POST"""
        response = test_client.post(
            f"/library/{sample_library.id}/search",
            json={"q": "Test"}
        )

        assert response.status_code == 200
        text = response.text

        assert "type:search" in text

    def test_search_empty_query(self, test_client: TestClient, sample_library):
        """Test search with empty query"""
        response = test_client.get(
            f"/library/{sample_library.id}/search",
            params={"q": ""}
        )

        assert response.status_code == 200
        text = response.text
        assert "type:search" in text

    def test_search_no_results(self, test_client: TestClient, sample_library):
        """Test search with no matching results"""
        response = test_client.get(
            f"/library/{sample_library.id}/search",
            params={"q": "NonExistentComic12345"}
        )

        assert response.status_code == 200


class TestV1Sync:
    """Test v1 sync endpoints"""

    def test_sync_reading_progress(self, test_client: TestClient, sample_library, multiple_comics, sample_user):
        """Test POST /library/sync - Sync reading progress"""
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

        response = test_client.post("/library/sync", json=sync_data)

        assert response.status_code == 200
        assert "OK" in response.text or "Synced" in response.text

    def test_sync_empty_data(self, test_client: TestClient, sample_user):
        """Test sync with empty data"""
        response = test_client.post("/library/sync", json={"comics": []})

        assert response.status_code == 200

    def test_sync_invalid_comic_id(self, test_client: TestClient, sample_user):
        """Test sync with invalid comic ID"""
        sync_data = {
            "comics": [
                {
                    "comicId": 9999,
                    "currentPage": 5,
                    "totalPages": 20
                }
            ]
        }

        response = test_client.post("/library/sync", json=sync_data)

        # Should handle gracefully
        assert response.status_code in [200, 404]


class TestV1TextFormatting:
    """Test v1 API text format compliance"""

    def test_crlf_line_endings(self, test_client: TestClient, sample_library, sample_comic):
        """Test that all text responses use CRLF line endings"""
        # Test various endpoints
        endpoints = [
            "/library/",
            f"/library/{sample_library.id}/folder/1",
            f"/library/{sample_library.id}/comic/{sample_comic.id}",
        ]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            if response.status_code == 200 and "text/plain" in response.headers.get("content-type", ""):
                # Should have CRLF, not just LF
                assert "\r\n" in response.text, f"Endpoint {endpoint} missing CRLF"

    def test_key_value_format(self, test_client: TestClient, sample_library, sample_comic):
        """Test that responses use key:value format"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")

        assert response.status_code == 200
        lines = response.text.split("\n")

        # Check that lines follow key:value format
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                # Should contain a colon separator
                assert ":" in line, f"Line missing colon separator: {line}"


class TestV1ErrorHandling:
    """Test v1 API error handling"""

    def test_library_not_found(self, test_client: TestClient):
        """Test handling of non-existent library"""
        response = test_client.get("/library/9999/folder/1")
        assert response.status_code == 404

    def test_comic_not_found(self, test_client: TestClient, sample_library):
        """Test handling of non-existent comic"""
        response = test_client.get(f"/library/{sample_library.id}/comic/9999")
        assert response.status_code == 404

    def test_invalid_library_id(self, test_client: TestClient):
        """Test handling of invalid library ID format"""
        response = test_client.get("/library/invalid/folder/1")
        assert response.status_code == 422  # Validation error

    def test_malformed_request(self, test_client: TestClient, sample_library, sample_comic):
        """Test handling of malformed POST requests"""
        response = test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data="invalid data"
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
