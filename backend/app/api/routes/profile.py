import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserProfileUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])

_AVATAR_DIR = Path(__file__).resolve().parents[3] / "data" / "avatars"
_AVATAR_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(current_user, key, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Upload user avatar image."""
    ext = Path(file.filename or "avatar.png").suffix or ".png"
    filename = f"{current_user.id}{ext}"
    dest = _AVATAR_DIR / filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    current_user.avatar_url = f"/users/avatars/{filename}"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/avatars/{filename}")
def serve_avatar(filename: str):
    """Serve avatar image file."""
    path = _AVATAR_DIR / filename
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "Avatar not found")
    return FileResponse(path)


@router.get("/search", response_model=list[UserResponse])
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[User]:
    """Search users by name or email. Returns up to 20 matches."""
    pattern = f"%{q}%"
    results = (
        db.query(User)
        .filter(
            User.id != current_user.id,
            (User.full_name.ilike(pattern))
            | (User.email.ilike(pattern))
            | (User.specialty.ilike(pattern)),
        )
        .order_by(User.full_name)
        .limit(20)
        .all()
    )
    return results
