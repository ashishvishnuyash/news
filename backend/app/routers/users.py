"""
User self-service routes: profile management, password change, notifications.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import User, Notification
from app.schemas import (
    UserResponse,
    UserProfileUpdate,
    PasswordChange,
    NotificationResponse,
)
from app.auth import get_current_user, get_password_hash, verify_password

router = APIRouter(prefix="/api/users", tags=["User Profile"])


@router.get("/me/profile", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return authenticated user's full profile."""
    return current_user


@router.put("/me/profile", response_model=UserResponse)
async def update_my_profile(
    profile: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update authenticated user's email and/or bio."""
    # Check email uniqueness if changing
    if profile.email and profile.email != current_user.email:
        result = await db.execute(
            select(User).filter(User.email == profile.email, User.id != current_user.id)
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That email address is already registered to another account.",
            )
        current_user.email = profile.email

    if profile.bio is not None:
        current_user.bio = profile.bio

    for field in ("profile_image_url", "job_title", "coverage_areas", "social_links"):
        value = getattr(profile, field)
        if value is not None:
            setattr(current_user, field, value.strip() or None)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/me/password")
async def change_password(
    pwd: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change authenticated user's password."""
    if not verify_password(pwd.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.hashed_password = get_password_hash(pwd.new_password)
    db.add(current_user)
    await db.commit()
    return {"status": "success", "message": "Password updated successfully."}


# ──────────────────────────────────────────────────────────────
# Notifications
# ──────────────────────────────────────────────────────────────

@router.get("/me/notifications", response_model=List[NotificationResponse])
async def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all notifications for the authenticated user."""
    result = await db.execute(
        select(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.put("/me/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    result = await db.execute(
        select(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalars().first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.is_read = True
    db.add(notif)
    await db.commit()
    return {"status": "success"}


@router.put("/me/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    result = await db.execute(
        select(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    for notif in result.scalars().all():
        notif.is_read = True
        db.add(notif)
    await db.commit()
    return {"status": "success", "message": "All notifications marked as read."}
