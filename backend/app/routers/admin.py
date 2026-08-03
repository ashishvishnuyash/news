"""
Admin-only routes: user management, role assignment, stats, article oversight.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.database import get_db
from app.models import User, Article, Comment, ReviewComment, Notification
from app.schemas import (
    AdminStats,
    AdminUserCreate,
    AdminUserUpdate,
    ArticleResponse,
    UserResponse,
    UserUpdateRole,
)
from app.auth import get_password_hash, require_role

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])


# ──────────────────────────────────────────────────────────────
# Dashboard Stats
# ──────────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStats)
async def get_stats(
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated platform statistics for the admin dashboard."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_articles = (await db.execute(select(func.count(Article.id)))).scalar()
    published = (await db.execute(select(func.count(Article.id)).filter(Article.status == "PUBLISHED"))).scalar()
    draft = (await db.execute(select(func.count(Article.id)).filter(Article.status == "DRAFT"))).scalar()
    submitted = (await db.execute(select(func.count(Article.id)).filter(Article.status == "SUBMITTED"))).scalar()
    rejected = (await db.execute(select(func.count(Article.id)).filter(Article.status == "REJECTED"))).scalar()
    total_comments = (await db.execute(select(func.count(Comment.id)))).scalar()
    journalists = (await db.execute(select(func.count(User.id)).filter(User.role == "JOURNALIST"))).scalar()
    editors = (await db.execute(select(func.count(User.id)).filter(User.role == "EDITOR"))).scalar()
    readers = (await db.execute(select(func.count(User.id)).filter(User.role == "READER"))).scalar()
    superadmins = (await db.execute(select(func.count(User.id)).filter(User.role == "SUPER_ADMIN"))).scalar()

    return AdminStats(
        total_users=total_users,
        total_articles=total_articles,
        published_articles=published,
        draft_articles=draft,
        submitted_articles=submitted,
        rejected_articles=rejected,
        total_comments=total_comments,
        total_journalists=journalists,
        total_editors=editors,
        total_readers=readers,
        total_superadmins=superadmins,
    )


# ──────────────────────────────────────────────────────────────
# User Management
# ──────────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """List all registered users."""
    query = select(User).order_by(User.id.asc())
    result = await db.execute(query)
    return result.scalars().all()


def ensure_role_assignment_allowed(actor: User, current_role: str, new_role: str) -> None:
    protected_roles = {"ADMIN", "SUPER_ADMIN"}
    if actor.role != "SUPER_ADMIN" and (
        current_role in protected_roles or new_role in protected_roles
    ):
        raise HTTPException(status_code=403, detail="Only the publisher can manage administrator roles")


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Create a user account with an explicitly assigned role."""
    ensure_role_assignment_allowed(current_user, "READER", payload.role)
    duplicate_filter = User.username == payload.username
    if payload.email:
        duplicate_filter = duplicate_filter | (User.email == payload.email.strip().lower())
    existing = await db.execute(select(User).filter(duplicate_filter))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Username or email already exists")
    user = User(
        username=payload.username,
        email=payload.email.strip().lower() if payload.email else None,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        bio=payload.bio.strip() if payload.bio else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Edit account details, role, and active state."""
    user = (await db.execute(select(User).filter(User.id == user_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    next_role = data.get("role", user.role)
    ensure_role_assignment_allowed(current_user, user.role, next_role)
    if user_id == current_user.id and (
        next_role != current_user.role or data.get("is_active") is False
    ):
        raise HTTPException(status_code=400, detail="You cannot demote or suspend your own account")
    if data.get("email"):
        email = data["email"].strip().lower()
        duplicate = await db.execute(select(User).filter(User.email == email, User.id != user_id))
        if duplicate.scalars().first():
            raise HTTPException(status_code=409, detail="Email already belongs to another account")
        data["email"] = email
    for field, value in data.items():
        setattr(user, field, value.strip() if field == "bio" and value else value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: UserUpdateRole,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role. Admins cannot demote themselves unless they are Super Admin."""
    if user_id == current_user.id and role_update.role != current_user.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role. Ask another publisher to make that change.",
        )

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ensure_role_assignment_allowed(current_user, user.role, role_update.role)

    old_role = user.role
    user.role = role_update.role
    db.add(user)

    # Notify the user of their role change
    notif = Notification(
        user_id=user.id,
        message=f"Your role has been changed from {old_role} to {role_update.role} by an administrator.",
        type="INFO",
        link="/",
    )
    db.add(notif)

    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Toggle user active/suspended status."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="You cannot suspend your own account."
        )

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != "SUPER_ADMIN" and user.role in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Only the publisher can suspend administrators")

    user.is_active = not user.is_active
    db.add(user)
    await db.commit()
    return {
        "status": "success",
        "is_active": user.is_active,
        "message": f"User {'activated' if user.is_active else 'suspended'} successfully.",
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a user and their content."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != "SUPER_ADMIN" and user.role in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Only the publisher can remove administrators")

    authored = (await db.execute(select(func.count(Article.id)).filter(Article.author_id == user.id))).scalar() or 0
    comments = (await db.execute(select(func.count(Comment.id)).filter(Comment.author_id == user.id))).scalar() or 0
    reviews = (await db.execute(select(func.count(ReviewComment.id)).filter(ReviewComment.author_id == user.id))).scalar() or 0
    if authored or comments or reviews:
        raise HTTPException(
            status_code=409,
            detail="This account has publication history and cannot be deleted. Suspend it to preserve the audit record.",
        )

    await db.delete(user)
    await db.commit()
    return {"status": "success", "message": "User deleted permanently."}


# ──────────────────────────────────────────────────────────────
# Article Management (Admin)
# ──────────────────────────────────────────────────────────────

@router.get("/articles", response_model=List[ArticleResponse])
async def list_all_articles(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_role(["ADMIN", "EDITOR"])),
    db: AsyncSession = Depends(get_db),
):
    """List all articles with optional status filter (admin/editor view)."""
    from sqlalchemy.orm import selectinload

    query = select(Article).options(
        selectinload(Article.author),
        selectinload(Article.editor),
    )
    if status_filter:
        query = query.filter(Article.status == status_filter.upper())
    query = query.order_by(Article.updated_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
