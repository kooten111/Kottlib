"""Compatibility tests for v2 favorites endpoints."""

import time

from src.constants import DEFAULT_USER
from src.database.models import Favorite, User


def _ensure_default_user(test_db):
    with test_db.get_session() as session:
        user = session.query(User).filter(User.username == DEFAULT_USER).first()
        if user:
            return user.id

        user = User(
            username=DEFAULT_USER,
            password_hash="changeme",
            is_admin=True,
            is_active=True,
            created_at=int(time.time()),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def test_v2_favorites_returns_text_plain_yac_schema(test_client, test_db, sample_library, sample_comic):
    user_id = _ensure_default_user(test_db)

    with test_db.get_session() as session:
        session.add(
            Favorite(
                user_id=user_id,
                library_id=sample_library.id,
                comic_id=sample_comic.id,
                created_at=int(time.time()),
            )
        )
        session.commit()

    response = test_client.get(f"/v2/library/{sample_library.id}/favs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    assert item["type"] == "comic"
    assert item["comic_info_id"] == str(sample_comic.id)
    assert item["library_id"] == str(sample_library.id)
    assert "file_name" in item
    assert "file_size" in item
    assert "hash" in item
    assert "cover_size_ratio" in item
    assert "has_been_opened" in item


def test_v2_favorites_add_and_remove_routes_work(test_client, test_db, sample_library, sample_comic):
    user_id = _ensure_default_user(test_db)

    add_response = test_client.post(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/fav")
    assert add_response.status_code == 200

    with test_db.get_session() as session:
        favorite = session.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.comic_id == sample_comic.id,
        ).first()
        assert favorite is not None

    remove_response = test_client.delete(f"/v2/library/{sample_library.id}/comic/{sample_comic.id}/fav")
    assert remove_response.status_code == 200

    with test_db.get_session() as session:
        favorite = session.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.comic_id == sample_comic.id,
        ).first()
        assert favorite is None
