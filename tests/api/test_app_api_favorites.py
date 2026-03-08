"""Tests for app-native favorites compatibility endpoints."""


def test_api_favorites_returns_json_and_alias_fields(test_client, sample_library, sample_comic):
    add_response = test_client.post(f"/api/favorites/{sample_comic.id}")
    assert add_response.status_code == 200

    response = test_client.get("/api/favorites")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    assert item["comic_info_id"] == str(sample_comic.id)
    assert item["comic_id"] == sample_comic.id
    assert item["comicId"] == sample_comic.id
    assert item["libraryId"] == sample_library.id
    assert item["library_id"] == sample_library.id
    assert "coverHash" in item
    assert "cover_hash" in item


def test_api_favorites_add_remove_bridge_to_v2_signature(test_client, sample_comic):
    add_response = test_client.post(f"/api/favorites/{sample_comic.id}")
    assert add_response.status_code == 200

    check_response = test_client.get(f"/api/favorites/{sample_comic.id}/check")
    assert check_response.status_code == 200
    assert check_response.json().get("isFavorite") is True

    remove_response = test_client.delete(f"/api/favorites/{sample_comic.id}")
    assert remove_response.status_code == 200

    check_response = test_client.get(f"/api/favorites/{sample_comic.id}/check")
    assert check_response.status_code == 200
    assert check_response.json().get("isFavorite") is False
