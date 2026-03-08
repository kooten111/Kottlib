"""Compatibility tests for YACReader-style v2 reading list endpoints."""

import json
import time

from src.database.models import ReadingList, ReadingListItem


def _create_reading_list_with_item(test_db, sample_library, sample_comic):
    with test_db.get_session() as session:
        reading_list = ReadingList(
            library_id=sample_library.id,
            user_id=None,
            name="Compat List",
            description="",
            is_public=True,
            position=0,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        session.add(reading_list)
        session.flush()

        session.add(
            ReadingListItem(
                reading_list_id=reading_list.id,
                comic_id=sample_comic.id,
                position=0,
                added_at=int(time.time()),
            )
        )
        session.commit()
        return reading_list.id


def test_v2_reading_lists_uses_yac_schema_and_text_plain(test_client, test_db, sample_library, sample_comic):
    _create_reading_list_with_item(test_db, sample_library, sample_comic)

    response = test_client.get(f"/v2/library/{sample_library.id}/reading_lists")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/plain")

    data = json.loads(response.text)
    assert isinstance(data, list)
    assert len(data) > 0

    item = data[0]
    assert item["type"] == "reading_list"
    assert "reading_list_name" in item
    assert "library_id" in item
    assert "library_uuid" in item


def test_v2_reading_list_info_uses_yac_schema(test_client, test_db, sample_library, sample_comic):
    list_id = _create_reading_list_with_item(test_db, sample_library, sample_comic)

    response = test_client.get(f"/v2/library/{sample_library.id}/reading_list/{list_id}/info")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/plain")

    data = json.loads(response.text)
    assert data["type"] == "reading_list"
    assert data["id"] == str(list_id)
    assert data["library_id"] == str(sample_library.id)
    assert data["reading_list_name"] == "Compat List"


def test_v2_reading_list_content_uses_yac_comic_shape(test_client, test_db, sample_library, sample_comic):
    list_id = _create_reading_list_with_item(test_db, sample_library, sample_comic)

    response = test_client.get(f"/v2/library/{sample_library.id}/reading_list/{list_id}/content")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/plain")

    data = json.loads(response.text)
    assert isinstance(data, list)
    assert len(data) == 1

    comic = data[0]
    assert comic["type"] == "comic"
    assert comic["id"] == str(sample_comic.id)
    assert comic["library_id"] == str(sample_library.id)
    assert "file_name" in comic
    assert "path" in comic
    assert "hash" in comic
