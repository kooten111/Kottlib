"""Tests for app-native reading list compatibility endpoints."""

import time

from src.database.models import ReadingList


def test_api_reading_lists_include_alias_fields(test_client, test_db, sample_library):
    with test_db.get_session() as session:
        reading_list = ReadingList(
            library_id=sample_library.id,
            user_id=None,
            name="Public List",
            description=None,
            is_public=True,
            position=0,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        session.add(reading_list)
        session.commit()

    response = test_client.get(f"/api/libraries/{sample_library.id}/reading-lists")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    assert item["libraryId"] == sample_library.id
    assert item["library_id"] == sample_library.id
    assert "comicCount" in item
    assert "comic_count" in item
    assert item["isPublic"] is True
    assert item["is_public"] is True
    assert item["description"] == ""


def test_api_create_reading_list_accepts_json_body(test_client, sample_library):
    response = test_client.post(
        f"/api/libraries/{sample_library.id}/reading-lists",
        json={
            "name": "Mobile Body List",
            "description": "created from json body",
            "isPublic": True,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["name"] == "Mobile Body List"
    assert data["isPublic"] is True
    assert data["is_public"] is True


def test_api_update_reading_list_accepts_camel_case_is_public(test_client, sample_library):
    create_response = test_client.post(
        f"/api/libraries/{sample_library.id}/reading-lists",
        json={"name": "Needs Update"},
    )
    assert create_response.status_code == 200
    list_id = create_response.json()["id"]

    update_response = test_client.patch(
        f"/api/libraries/{sample_library.id}/reading-lists/{list_id}",
        json={"isPublic": True},
    )
    assert update_response.status_code == 200

    update_data = update_response.json()
    assert update_data["success"] is True
    assert update_data["isPublic"] is True
    assert update_data["is_public"] is True
