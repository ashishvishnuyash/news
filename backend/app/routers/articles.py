from typing import Optional, List
from datetime import datetime, timezone
import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Article, User, Notification, utc_now
from app.schemas import ArticleCreate, ArticleUpdate, ArticleResponse
from app.auth import get_current_user, require_role
from app.content import sanitize_article_html


def get_token(request: Request) -> Optional[str]:
    """Extract JWT token from cookie or Authorization header."""
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    return token


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


async def generate_unique_slug(title: str, db: AsyncSession, exclude_id: Optional[int] = None) -> str:
    base_slug = slugify(title) or "article"
    slug = base_slug
    counter = 1
    while True:
        query = select(Article).filter(Article.slug == slug)
        if exclude_id:
            query = query.filter(Article.id != exclude_id)
        res = await db.execute(query)
        if not res.scalars().first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


router = APIRouter(prefix="/api/articles", tags=["Articles"])


def database_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Store editor-entered timestamps as naive UTC for SQLite/PostgreSQL parity."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# ──────────────────────────────────────────────────────────────
# Public Endpoints
# ──────────────────────────────────────────────────────────────

@router.get("", response_model=List[ArticleResponse])
async def list_articles(
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List published articles. Supports category filter and full-text search."""
    query = (
        select(Article)
        .filter(Article.status == "PUBLISHED")
        .options(selectinload(Article.author), selectinload(Article.editor))
    )
    if category and category.lower() != "all":
        query = query.filter(Article.category.ilike(category))
    if q:
        search = f"%{q}%"
        query = query.filter(
            (Article.title.ilike(search))
            | (Article.content.ilike(search))
            | (Article.summary.ilike(search))
            | (Article.tags.ilike(search))
        )
    query = query.order_by(Article.is_pinned.desc(), Article.published_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()



# ──────────────────────────────────────────────────────────────
# Staff Endpoints (must come before /{slug_or_id} to avoid conflicts)
# ──────────────────────────────────────────────────────────────

@router.get("/journalist/my", response_model=List[ArticleResponse])
async def list_my_articles(
    current_user: User = Depends(require_role(["JOURNALIST", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Return all articles written by the currently logged-in journalist."""
    query = (
        select(Article)
        .filter(Article.author_id == current_user.id)
        .options(selectinload(Article.author), selectinload(Article.editor))
        .order_by(Article.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/editor/queue", response_model=List[ArticleResponse])
async def list_editor_queue(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_role(["EDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Return articles in the editorial queue. Filter by status."""
    query = select(Article).options(
        selectinload(Article.author), selectinload(Article.editor)
    )
    normalized_status = status_filter.upper() if status_filter else None
    if normalized_status and normalized_status != "ALL":
        if normalized_status not in {"DRAFT", "FACT_CHECK", "EDITOR_REVIEW", "APPROVED", "SCHEDULED", "SUBMITTED", "PUBLISHED", "REJECTED"}:
            raise HTTPException(status_code=400, detail="Invalid article status filter")
        query = query.filter(Article.status == normalized_status)
    elif normalized_status is None:
        query = query.filter(Article.status == "SUBMITTED")
    query = query.order_by(Article.updated_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# ──────────────────────────────────────────────────────────────
# Single Article (public + optional auth for drafts)
# ──────────────────────────────────────────────────────────────

@router.get("/{slug_or_id}", response_model=ArticleResponse)
async def get_article(
    slug_or_id: str,
    track_view: bool = Query(default=True, description="Increment the public view counter"),
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(get_token),
):
    """Get a single article by slug or numeric ID."""
    if slug_or_id.isdigit():
        query = select(Article).filter(Article.id == int(slug_or_id))
    else:
        query = select(Article).filter(Article.slug == slug_or_id)

    query = query.options(
        selectinload(Article.author), selectinload(Article.editor)
    )
    result = await db.execute(query)
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment view count for published articles
    if article.status == "PUBLISHED" and track_view:
        article.view_count = (article.view_count or 0) + 1
        db.add(article)
        await db.commit()
        await db.refresh(article)

    # Non-published: require auth and proper role
    if article.status != "PUBLISHED":
        if not token:
            raise HTTPException(status_code=403, detail="Not authorized to view unpublished articles")
        try:
            from jose import jwt, JWTError
            from app.config import settings

            clean = token.replace("Bearer ", "") if token.startswith("Bearer ") else token
            payload = jwt.decode(clean, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username = payload.get("sub")
            user_res = await db.execute(select(User).filter(User.username == username))
            user = user_res.scalars().first()

            if not user or not user.is_active:
                raise HTTPException(status_code=403, detail="Not authorized")
            if user.role not in ["EDITOR", "ADMIN", "SUPER_ADMIN"] and article.author_id != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to view this draft")
        except JWTError:
            raise HTTPException(status_code=403, detail="Not authorized to view this draft")

    return article


# ──────────────────────────────────────────────────────────────
# Create Article
# ──────────────────────────────────────────────────────────────

@router.post("", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_in: ArticleCreate,
    current_user: User = Depends(require_role(["JOURNALIST", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Create a new article draft."""
    slug = await generate_unique_slug(article_in.slug or article_in.title, db)
    clean_content = sanitize_article_html(article_in.content)
    author_id = current_user.id
    if article_in.author_id and article_in.author_id != current_user.id:
        if current_user.role not in ["ADMIN", "SUPER_ADMIN"]:
            raise HTTPException(status_code=403, detail="Only administrators can assign another author")
        assigned_author = (await db.execute(select(User).filter(User.id == article_in.author_id))).scalars().first()
        if not assigned_author or assigned_author.role not in ["JOURNALIST", "EDITOR", "ADMIN", "SUPER_ADMIN"]:
            raise HTTPException(status_code=400, detail="Choose a valid newsroom author")
        author_id = assigned_author.id
    db_article = Article(
        title=article_in.title,
        slug=slug,
        subtitle=article_in.subtitle.strip() if article_in.subtitle else None,
        content=clean_content,
        summary=article_in.summary.strip(),
        category=article_in.category,
        image_url=article_in.image_url,
        image_caption=article_in.image_caption.strip() if article_in.image_caption else None,
        tags=article_in.tags,
        sources=article_in.sources.strip() if article_in.sources else None,
        seo_title=article_in.seo_title.strip() if article_in.seo_title else None,
        seo_description=article_in.seo_description.strip() if article_in.seo_description else None,
        og_image_url=article_in.og_image_url,
        article_type=article_in.article_type,
        fact_check_rating=article_in.fact_check_rating,
        scheduled_at=database_datetime(article_in.scheduled_at),
        status="DRAFT",
        author_id=author_id,
    )
    db.add(db_article)
    await db.commit()

    query = (
        select(Article)
        .filter(Article.id == db_article.id)
        .options(selectinload(Article.author), selectinload(Article.editor))
    )
    res = await db.execute(query)
    return res.scalars().first()


# ──────────────────────────────────────────────────────────────
# Update Article
# ──────────────────────────────────────────────────────────────

@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing article. Supports status transitions."""
    query = (
        select(Article)
        .filter(Article.id == article_id)
        .options(selectinload(Article.author), selectinload(Article.editor))
    )
    result = await db.execute(query)
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    is_author = article.author_id == current_user.id
    is_editor = current_user.role in ["EDITOR", "ADMIN", "SUPER_ADMIN"]

    if not is_author and not is_editor:
        raise HTTPException(status_code=403, detail="Not authorized to edit this article")

    if is_author and not is_editor:
        if article.status not in ["DRAFT", "REJECTED"]:
            raise HTTPException(
                status_code=400,
                detail="You can only edit articles that are in DRAFT or REJECTED status.",
            )

    update_data = article_update.model_dump(exclude_unset=True)

    if "scheduled_at" in update_data:
        update_data["scheduled_at"] = database_datetime(update_data["scheduled_at"])

    if "content" in update_data:
        update_data["content"] = sanitize_article_html(update_data["content"])
    if "summary" in update_data and update_data["summary"] is not None:
        update_data["summary"] = update_data["summary"].strip()
    for text_field in ("subtitle", "sources", "seo_title", "seo_description"):
        if text_field in update_data and update_data[text_field] is not None:
            update_data[text_field] = update_data[text_field].strip() or None
    effective_image = update_data.get("image_url", article.image_url)
    if not effective_image:
        update_data["image_url"] = None
        update_data["image_caption"] = None
    elif "image_caption" in update_data and update_data["image_caption"] is not None:
        update_data["image_caption"] = update_data["image_caption"].strip() or None

    if not is_editor and ({"is_pinned", "is_breaking"} & update_data.keys()):
        raise HTTPException(status_code=403, detail="Only editors can change front-page placement")

    if "author_id" in update_data and update_data["author_id"] != article.author_id:
        if not is_editor:
            raise HTTPException(status_code=403, detail="Only editors can reassign an article")
        assigned_author = (await db.execute(select(User).filter(User.id == update_data["author_id"]))).scalars().first()
        if not assigned_author or assigned_author.role not in ["JOURNALIST", "EDITOR", "ADMIN", "SUPER_ADMIN"]:
            raise HTTPException(status_code=400, detail="Choose a valid newsroom author")

    if "slug" in update_data:
        requested_slug = slugify(update_data.pop("slug"))
        if not requested_slug:
            raise HTTPException(status_code=400, detail="Slug cannot be empty")
        duplicate = (await db.execute(select(Article).filter(
            Article.slug == requested_slug,
            Article.id != article.id,
        ))).scalars().first()
        if duplicate:
            raise HTTPException(status_code=409, detail="That article slug is already in use")
        article.slug = requested_slug

    # Handle status transitions
    new_status = update_data.get("status")
    if new_status:
        effective_summary = update_data.get("summary", article.summary)
        if new_status in ["FACT_CHECK", "EDITOR_REVIEW", "APPROVED", "SCHEDULED", "SUBMITTED", "PUBLISHED"] and not (effective_summary and effective_summary.strip()):
            raise HTTPException(status_code=400, detail="A written summary is required before submission")
        if new_status == "SCHEDULED" and not update_data.get("scheduled_at", article.scheduled_at):
            raise HTTPException(status_code=400, detail="Choose a publication time before scheduling")
        if is_author and not is_editor:
            if new_status not in ["DRAFT", "FACT_CHECK", "EDITOR_REVIEW", "SUBMITTED"]:
                raise HTTPException(status_code=400, detail="Invalid status transition for journalist")
        elif is_editor:
            previous_status = article.status
            if new_status == "PUBLISHED" and previous_status != "PUBLISHED":
                # SQLAlchemy's DateTime columns are timezone-naive in this schema.
                # asyncpg rejects an aware datetime for PostgreSQL TIMESTAMP columns.
                article.published_at = utc_now()
                article.editor_id = current_user.id
                notif = Notification(
                    user_id=article.author_id,
                    message=f"Your article '{article.title}' has been published!",
                    type="SUCCESS",
                    link=f"/articles/{article.slug}",
                )
                db.add(notif)
            elif new_status == "REJECTED" and previous_status != "REJECTED":
                article.editor_id = current_user.id
                notif = Notification(
                    user_id=article.author_id,
                    message=f"Your article '{article.title}' was returned for revisions.",
                    type="WARNING",
                    link=f"/articles/{article.slug}",
                )
                db.add(notif)
            elif previous_status == "PUBLISHED" and new_status != "PUBLISHED":
                article.published_at = None

    # Regenerate slug if title changed and not yet published
    if (
        "title" in update_data
        and update_data["title"] != article.title
        and article.status != "PUBLISHED"
        and article.slug == slugify(article.title)
    ):
        article.slug = await generate_unique_slug(update_data["title"], db, exclude_id=article.id)

    for key, value in update_data.items():
        setattr(article, key, value)

    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


# ──────────────────────────────────────────────────────────────
# Delete Article
# ──────────────────────────────────────────────────────────────

@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an article. Authors can delete their own DRAFT/REJECTED articles. Admins can delete anything."""
    result = await db.execute(select(Article).filter(Article.id == article_id))
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    is_author = article.author_id == current_user.id
    is_admin = current_user.role in ["ADMIN", "SUPER_ADMIN"]

    if not is_author and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this article")

    if is_author and not is_admin:
        if article.status not in ["DRAFT", "REJECTED"]:
            raise HTTPException(
                status_code=400,
                detail="You can only delete DRAFT or REJECTED articles.",
            )

    await db.delete(article)
    await db.commit()
    return {"status": "success", "message": "Article deleted successfully"}
