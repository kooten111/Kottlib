"""
User Interactions API Router

Provides endpoints for managing user-specific data:
- Favorites
- Labels (Tags)
- Reading Lists
"""

from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel

from ...database.models import Favorite, Label, ComicLabel, ReadingList, ReadingListItem, Comic
from ..middleware import get_current_user_id, get_request_user
from ...database import get_user_by_id, get_user_by_username

router = APIRouter(tags=["user-interactions"])

# ============================================================================
# Pydantic Models
# ============================================================================

class FavoriteModel(BaseModel):
    comic_id: int
    library_id: int
    created_at: int

class LabelModel(BaseModel):
    id: int
    name: str
    color_id: int

class ReadingListModel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_public: bool

# ============================================================================
# Favorites
# ============================================================================

@router.get("/favorites", response_model=List[FavoriteModel])
async def get_favorites(request: Request):
    """Get user's favorite comics"""
    db = request.app.state.db

    with db.get_session() as session:
        # Fallback to admin for single-user mode
        user = get_request_user(request, session)
        if not user:
            return []
        user_id = user.id

        favorites = session.query(Favorite).filter(Favorite.user_id == user_id).all()
        return [
            FavoriteModel(
                comic_id=f.comic_id,
                library_id=f.library_id,
                created_at=f.created_at
            ) for f in favorites
        ]

@router.post("/favorites/{comic_id}")
async def add_favorite(comic_id: int, request: Request):
    """Add a comic to favorites"""
    import time
    db = request.app.state.db

    with db.get_session() as session:
        user = get_request_user(request, session)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        user_id = user.id

        # Check if comic exists
        comic = session.query(Comic).filter(Comic.id == comic_id).first()
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")
            
        # Check if already favorite
        existing = session.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.comic_id == comic_id
        ).first()
        
        if existing:
            return {"success": True, "message": "Already in favorites"}
            
        favorite = Favorite(
            user_id=user_id,
            library_id=comic.library_id,
            comic_id=comic_id,
            created_at=int(time.time())
        )
        session.add(favorite)
        session.commit()
        
        return {"success": True}

@router.delete("/favorites/{comic_id}")
async def remove_favorite(comic_id: int, request: Request):
    """Remove a comic from favorites"""
    db = request.app.state.db

    with db.get_session() as session:
        user = get_request_user(request, session)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        user_id = user.id

        session.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.comic_id == comic_id
        ).delete()
        session.commit()
        
        return {"success": True}

# ============================================================================
# Labels (Tags)
# ============================================================================

@router.get("/labels", response_model=List[LabelModel])
async def get_labels(library_id: int, request: Request):
    """Get all labels for a library"""
    db = request.app.state.db
    
    with db.get_session() as session:
        labels = session.query(Label).filter(Label.library_id == library_id).all()
        return [
            LabelModel(
                id=l.id,
                name=l.name,
                color_id=l.color_id
            ) for l in labels
        ]

@router.post("/labels")
async def create_label(library_id: int, name: str, color_id: int, request: Request):
    """Create a new label"""
    import time
    db = request.app.state.db
    
    with db.get_session() as session:
        # Check if exists
        existing = session.query(Label).filter(
            Label.library_id == library_id,
            Label.name == name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Label already exists")
            
        label = Label(
            library_id=library_id,
            name=name,
            color_id=color_id,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        session.add(label)
        session.commit()
        session.refresh(label)
        
        return LabelModel(id=label.id, name=label.name, color_id=label.color_id)

# ============================================================================
# Reading Lists
# ============================================================================

@router.get("/lists", response_model=List[ReadingListModel])
async def get_reading_lists(library_id: int, request: Request):
    """Get reading lists for a library"""
    db = request.app.state.db
    
    with db.get_session() as session:
        lists = session.query(ReadingList).filter(ReadingList.library_id == library_id).all()
        return [
            ReadingListModel(
                id=l.id,
                name=l.name,
                description=l.description,
                is_public=l.is_public
            ) for l in lists
        ]
