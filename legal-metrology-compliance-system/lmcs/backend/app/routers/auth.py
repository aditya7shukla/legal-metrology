from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole, AuditLog
from app.schemas import UserCreate, UserOut, Token, LoginRequest, RefreshRequest
from app.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, get_current_user, require_roles,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _log(db: Session, request: Request, user_id: str | None, action: str, details: dict | None = None):
    db.add(AuditLog(
        user_id=user_id, action=action, ip_address=request.client.host if request.client else None,
        details=details or {},
    ))
    db.commit()


@router.post("/register", response_model=UserOut, status_code=201)
def register_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Admin-only: create new enforcement officer / viewer / admin accounts."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        designation=payload.designation,
        jurisdiction=payload.jurisdiction,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _log(db, request, current_user.id, "USER_CREATED", {"new_user_id": user.id, "role": user.role.value})
    return user


@router.post("/bootstrap-admin", response_model=UserOut, status_code=201)
def bootstrap_admin(payload: UserCreate, db: Session = Depends(get_db)):
    """
    One-time-use endpoint to create the FIRST admin account when the system
    has no users. Automatically disabled once any user exists.
    """
    if db.query(User).count() > 0:
        raise HTTPException(status_code=403, detail="System already initialized. Use /auth/register as an admin.")
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.ADMIN,
        designation=payload.designation,
        jurisdiction=payload.jurisdiction,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        _log(db, request, None, "LOGIN_FAILED", {"email": payload.email})
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact your administrator.")
    _log(db, request, user.id, "LOGIN_SUCCESS")
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=user,
    )


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    user = db.query(User).filter(User.id == data.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=user,
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
