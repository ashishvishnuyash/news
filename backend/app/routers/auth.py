from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserRegister, UserResponse
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.config import settings
from app.site_config import feature_enabled

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a reader account. The first account bootstraps the publisher role."""
    count_result = await db.execute(select(func.count(User.id)))
    user_count = count_result.scalar() or 0
    if user_count > 0 and not await feature_enabled(db, "registration_open", True):
        raise HTTPException(status_code=403, detail="New reader registration is currently closed.")
    # Check if username exists
    result = await db.execute(select(User).filter(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken. Please choose another."
        )

    # Check if email is taken (if provided)
    if user_in.email:
        email_result = await db.execute(select(User).filter(User.email == user_in.email))
        if email_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered."
            )

    # The initial account must be able to configure the publication and delegate roles.
    role = "SUPER_ADMIN" if user_count == 0 else "READER"

    hashed_pwd = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email or None,
        hashed_password=hashed_pwd,
        role=role,
        slug=user_in.username.lower(),
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login")
async def login(
    response: Response,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT access token."""
    result = await db.execute(select(User).filter(User.username == user_in.username))
    user = result.scalars().first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Contact an administrator.",
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
        domain=settings.COOKIE_DOMAIN,
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/logout")
async def logout(response: Response):
    """Clear server-side session cookie."""
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
