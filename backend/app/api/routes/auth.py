import secrets
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import GoogleLoginRequest, RegisterRequest, Token
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_LOCK = threading.Lock()


def _rate_limit_key(request: Request, username: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}:{username.lower().strip()}"


def _check_login_rate_limit(request: Request, username: str) -> None:
    now = time.time()
    window = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
    limit = settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS
    key = _rate_limit_key(request, username)

    with _LOGIN_LOCK:
        attempts = [ts for ts in _LOGIN_ATTEMPTS.get(key, []) if now - ts <= window]
        if len(attempts) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )
        _LOGIN_ATTEMPTS[key] = attempts


def _record_login_failure(request: Request, username: str) -> None:
    now = time.time()
    window = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
    key = _rate_limit_key(request, username)
    with _LOGIN_LOCK:
        attempts = [ts for ts in _LOGIN_ATTEMPTS.get(key, []) if now - ts <= window]
        attempts.append(now)
        _LOGIN_ATTEMPTS[key] = attempts


def _clear_login_failures(request: Request, username: str) -> None:
    key = _rate_limit_key(request, username)
    with _LOGIN_LOCK:
        _LOGIN_ATTEMPTS.pop(key, None)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    _check_login_rate_limit(request, form_data.username)
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        _record_login_failure(request, form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    _clear_login_failures(request, form_data.username)
    token = create_access_token(user.id)
    return Token(access_token=token)


@router.post("/google", response_model=Token)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)) -> Token:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured",
        )

    try:
        info = google_id_token.verify_oauth2_token(
            payload.id_token,
            GoogleAuthRequest(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        ) from exc

    email = info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email missing",
        )
    if info.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email not verified",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        full_name = info.get("name") or info.get("given_name") or email
        random_password = secrets.token_urlsafe(24)
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(random_password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id)
    return Token(access_token=token)
