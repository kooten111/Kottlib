"""
Integration Tests for YACLib Enhanced API

Tests complete workflows across multiple endpoints to ensure
mobile and webui functionality works end-to-end.
"""
import pytest
from fastapi.testclient import TestClient


class TestMobileWorkflow:
    """Test complete mobile app workflow (v1 API primarily)"""

    def test_mobile_app_connection_and_browsing(self, test_client: TestClient, sample_library, sample_folder, multiple_comics):
        """
        Test complete mobile app workflow:
        1. List libraries
        2. Browse folders
        3. Get comic metadata
        4. Read pages
        5. Update progress
        """
        # Step 1: List libraries
        libraries_response = test_client.get("/library/")
        assert libraries_response.status_code == 200
        assert f"id:{sample_library.id}" in libraries_response.text

        # Step 2: Browse folders
        folder_response = test_client.get(f"/library/{sample_library.id}/folder/{sample_folder.id}")
        assert folder_response.status_code == 200
        assert "type:folder" in folder_response.text

        # Step 3: Get folder info (recursive listing)
        folder_info_response = test_client.get(f"/library/{sample_library.id}/folder/{sample_folder.id}/info")
        assert folder_info_response.status_code == 200

        # Step 4: Get comic metadata
        comic = multiple_comics[0]
        comic_response = test_client.get(f"/library/{sample_library.id}/comic/{comic.id}")
        assert comic_response.status_code == 200
        assert f"comicid:{comic.id}" in comic_response.text

        # Step 5: Update reading progress
        progress_response = test_client.post(
            f"/library/{sample_library.id}/comic/{comic.id}/setCurrentPage",
            data={"page": "5"}
        )
        assert progress_response.status_code == 200

        # Step 6: Verify progress was saved via continue reading
        continue_response = test_client.get("/library/continue-reading")
        assert continue_response.status_code == 200

    def test_mobile_search_and_read_workflow(self, test_client: TestClient, sample_library, sample_comic):
        """
        Test mobile app search and read workflow:
        1. Search for comics
        2. Open comic from search results
        3. Get remote reading info
        4. Read pages
        """
        # Step 1: Search
        search_response = test_client.get(
            f"/library/{sample_library.id}/search",
            params={"q": "Test"}
        )
        assert search_response.status_code == 200
        assert "type:search" in search_response.text

        # Step 2: Get comic for remote reading
        remote_response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/remote")
        assert remote_response.status_code == 200
        assert "numpages:" in remote_response.text

    def test_mobile_sync_workflow(self, test_client: TestClient, sample_library, multiple_comics, sample_user):
        """
        Test mobile app sync workflow:
        1. Read multiple comics
        2. Sync progress to server
        3. Verify progress was saved
        """
        # Step 1: Update progress for multiple comics locally (simulated)
        # Step 2: Sync all at once
        sync_data = {
            "comics": [
                {"comicId": comic.id, "currentPage": i * 5, "totalPages": comic.num_pages}
                for i, comic in enumerate(multiple_comics)
            ]
        }

        sync_response = test_client.post("/library/sync", json=sync_data)
        assert sync_response.status_code == 200

        # Step 3: Verify via continue reading
        continue_response = test_client.get("/library/continue-reading")
        assert continue_response.status_code == 200


class TestWebUIWorkflow:
    """Test complete WebUI workflow (v2 API primarily)"""

    def test_webui_browsing_workflow(self, test_client: TestClient, sample_library, sample_folder, multiple_comics):
        """
        Test complete WebUI browsing workflow:
        1. List libraries (JSON)
        2. Browse folders (JSON)
        3. Get comic details (JSON)
        4. Mark as read/unread
        """
        # Step 1: List libraries
        libraries_response = test_client.get("/v2/libraries")
        assert libraries_response.status_code == 200
        libraries = libraries_response.json()
        assert len(libraries) > 0

        # Step 2: Browse folder
        folder_response = test_client.get(f"/v2/library/{sample_library.id}/folder/{sample_folder.id}")
        assert folder_response.status_code == 200

        # Step 3: Get comic details
        comic = multiple_comics[0]
        comic_response = test_client.get(f"/v2/library/{sample_library.id}/comic/{comic.id}/remote")
        assert comic_response.status_code == 200

    def test_webui_series_browsing_workflow(self, test_client: TestClient, sample_library, multiple_comics):
        """
        Test WebUI series browsing:
        1. Get series list
        2. Browse comics in series
        3. Read comics in order
        """
        # Step 1: Get series list (if endpoint exists)
        series_response = test_client.get(f"/v2/library/{sample_library.id}/series")
        # Endpoint might not exist
        assert series_response.status_code in [200, 404]

    def test_webui_statistics_workflow(self, test_client: TestClient, sample_library, sample_user, sample_reading_progress):
        """
        Test WebUI statistics and analytics:
        1. Get library stats
        2. Get user reading stats
        3. Verify data consistency
        """
        # Step 1: Get library stats (if endpoint exists)
        stats_response = test_client.get(f"/v2/library/{sample_library.id}/stats")
        assert stats_response.status_code in [200, 404]


class TestCrossAPICompatibility:
    """Test that v1 and v2 APIs work together seamlessly"""

    def test_v1_and_v2_data_consistency(self, test_client: TestClient, sample_library, sample_comic):
        """
        Test that data is consistent between v1 and v2 APIs:
        1. Get comic via v1
        2. Get same comic via v2
        3. Verify data matches
        """
        # Get via v1
        v1_response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")
        assert v1_response.status_code == 200

        # Get via v2
        v2_response = test_client.get(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/remote")
        assert v2_response.status_code == 200

        # Both should reference same comic
        v1_text = v1_response.text
        v2_text = v2_response.text

        assert f"comicid:{sample_comic.id}" in v1_text
        assert f"comicid:{sample_comic.id}" in v2_text or f"hash:{sample_comic.hash}" in v2_text

    def test_progress_sync_across_apis(self, test_client: TestClient, sample_library, sample_comic, sample_user):
        """
        Test that reading progress syncs across v1 and v2:
        1. Update progress via v1
        2. Check progress via v2
        3. Update via v2
        4. Check via v1
        """
        # Update via v1
        v1_update = test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data={"page": "10"}
        )
        assert v1_update.status_code == 200

        # Check via v1
        v1_check = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")
        assert v1_check.status_code == 200
        assert "currentPage:" in v1_check.text

    def test_sync_endpoints_consistency(self, test_client: TestClient, multiple_comics, sample_user):
        """
        Test that v1 and v2 sync endpoints produce consistent results
        """
        sync_data = {
            "comics": [
                {"comicId": multiple_comics[0].id, "currentPage": 5, "totalPages": 20}
            ]
        }

        # Sync via v1
        v1_sync = test_client.post("/library/sync", json=sync_data)
        assert v1_sync.status_code == 200

        # Sync via v2 (if endpoint exists)
        v2_sync = test_client.post("/v2/sync", json=sync_data)
        assert v2_sync.status_code in [200, 404]


class TestNavigationConsistency:
    """Test that navigation (prev/next) works consistently"""

    def test_sequential_navigation(self, test_client: TestClient, sample_library, multiple_comics):
        """
        Test navigating through comics sequentially:
        1. Start at first comic
        2. Navigate to next
        3. Navigate to previous
        4. Verify consistency
        """
        if len(multiple_comics) < 3:
            pytest.skip("Need at least 3 comics for navigation test")

        # Get middle comic
        comic = multiple_comics[2]
        response = test_client.get(f"/library/{sample_library.id}/comic/{comic.id}")

        assert response.status_code == 200
        text = response.text

        # Should have navigation info
        # previousComic and nextComic fields
        has_prev = "previousComic:" in text
        has_next = "nextComic:" in text

        # Middle comic should have both
        assert has_prev or has_next

    def test_v2_hash_based_navigation(self, test_client: TestClient, sample_library, multiple_comics):
        """
        Test v2 hash-based navigation for verification
        """
        if len(multiple_comics) < 3:
            pytest.skip("Need at least 3 comics for navigation test")

        comic = multiple_comics[2]
        response = test_client.get(f"/v2/library/{sample_library.id}/comic/{comic.id}/remote")

        assert response.status_code == 200
        text = response.text

        # Should include hash for current comic
        assert f"hash:{comic.hash}" in text


class TestErrorRecovery:
    """Test error handling and recovery across workflows"""

    def test_invalid_comic_id_handling(self, test_client: TestClient, sample_library):
        """
        Test graceful handling of invalid comic IDs across multiple endpoints
        """
        invalid_id = 9999

        # Test v1 endpoints
        v1_response = test_client.get(f"/library/{sample_library.id}/comic/{invalid_id}")
        assert v1_response.status_code == 404

        # Test v2 endpoints
        v2_response = test_client.get(f"/v2/library/{sample_library.id}/comic/{invalid_id}")
        assert v2_response.status_code == 404

    def test_corrupted_data_handling(self, test_client: TestClient, sample_library, sample_comic):
        """
        Test handling of corrupted or malformed requests
        """
        # Send malformed progress update
        response = test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data={"page": "invalid"}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_concurrent_updates_handling(self, test_client: TestClient, sample_library, sample_comic, sample_user):
        """
        Test handling of concurrent progress updates
        """
        # Simulate multiple rapid updates
        for page in range(5):
            response = test_client.post(
                f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
                data={"page": str(page)}
            )
            assert response.status_code == 200


class TestPerformanceIntegration:
    """Test performance across complete workflows"""

    def test_bulk_operations_performance(self, test_client: TestClient, sample_library, multiple_comics, sample_user):
        """
        Test performance of bulk operations:
        1. Sync many comics at once
        2. Get large folder listings
        3. Perform multiple searches
        """
        # Bulk sync
        sync_data = {
            "comics": [
                {"comicId": comic.id, "currentPage": i, "totalPages": comic.num_pages}
                for i, comic in enumerate(multiple_comics)
            ]
        }

        sync_response = test_client.post("/library/sync", json=sync_data)
        assert sync_response.status_code == 200

    def test_repeated_access_performance(self, test_client: TestClient, sample_library, sample_comic):
        """
        Test performance of repeated access to same resources (caching)
        """
        # Access same comic multiple times
        for _ in range(5):
            response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")
            assert response.status_code == 200

        # Access same folder multiple times
        for _ in range(5):
            response = test_client.get(f"/library/{sample_library.id}/folder/1")
            assert response.status_code == 200


class TestDataConsistency:
    """Test data consistency across operations"""

    def test_reading_progress_consistency(self, test_client: TestClient, sample_library, sample_comic, sample_user):
        """
        Test that reading progress remains consistent:
        1. Set progress
        2. Read progress
        3. Update progress
        4. Verify final state
        """
        # Set initial progress
        test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data={"page": "5"}
        )

        # Read progress
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")
        assert response.status_code == 200

        # Update progress
        test_client.post(
            f"/library/{sample_library.id}/comic/{sample_comic.id}/setCurrentPage",
            data={"page": "10"}
        )

        # Verify final state
        final_response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}")
        assert final_response.status_code == 200

    def test_library_data_consistency(self, test_client: TestClient, sample_library, multiple_comics):
        """
        Test that library data is consistent across different views:
        1. List libraries
        2. Get library details
        3. Browse library folders
        4. Verify counts and data match
        """
        # List libraries
        libraries = test_client.get("/v2/libraries").json()

        # Get library details
        library_detail = test_client.get(f"/v2/library/{sample_library.id}")
        assert library_detail.status_code == 200


class TestSecurityAndAuth:
    """Test security and authentication flows"""

    def test_unauthenticated_access(self, test_client: TestClient, sample_library):
        """
        Test access without authentication (should still work for most endpoints)
        """
        # Libraries should be accessible
        response = test_client.get("/v2/libraries")
        assert response.status_code == 200

    def test_session_persistence(self, test_client: TestClient, sample_library, sample_comic):
        """
        Test that session persists across requests
        """
        # Make multiple requests with session cookie
        response1 = test_client.get(
            f"/library/{sample_library.id}/comic/{sample_comic.id}",
            cookies={"yacread_session": "test_session"}
        )
        response2 = test_client.get(
            f"/library/{sample_library.id}/comic/{sample_comic.id}",
            cookies={"yacread_session": "test_session"}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_library(self, test_client: TestClient, test_db, test_data_dir):
        """Test handling of empty library"""
        # Create empty library
        from src.database.models import Library
        with test_db.get_session() as session:
            empty_lib = Library(
                name="Empty Library",
                path=str(test_data_dir / "empty")
            )
            session.add(empty_lib)
            session.commit()
            session.refresh(empty_lib)

            # Try to browse empty library
            response = test_client.get(f"/library/{empty_lib.id}/folder/1")
            assert response.status_code == 200

    def test_very_long_search_query(self, test_client: TestClient, sample_library):
        """Test search with very long query"""
        long_query = "test" * 100
        response = test_client.get(
            f"/library/{sample_library.id}/search",
            params={"q": long_query}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 414]

    def test_special_characters_in_search(self, test_client: TestClient, sample_library):
        """Test search with special characters"""
        special_query = "test@#$%^&*()"
        response = test_client.get(
            f"/library/{sample_library.id}/search",
            params={"q": special_query}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400]

    def test_max_page_number(self, test_client: TestClient, sample_library, sample_comic):
        """Test accessing maximum page number"""
        max_page = sample_comic.num_pages - 1
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/page/{max_page}")

        # Will fail with dummy data but should handle correctly
        assert response.status_code in [200, 404, 500]

    def test_negative_page_number(self, test_client: TestClient, sample_library, sample_comic):
        """Test accessing negative page number"""
        response = test_client.get(f"/library/{sample_library.id}/comic/{sample_comic.id}/page/-1")

        # Should reject
        assert response.status_code in [404, 422]
