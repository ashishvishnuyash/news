"""Public newsroom discovery, transparency, newsletter, and live coverage APIs."""

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import require_role
from app.content import sanitize_article_html
from app.database import get_db
from app.models import (
    Article,
    Correction,
    LiveUpdate,
    NewsletterSubscriber,
    NewsroomMessage,
    Notification,
    User,
    utc_now,
)
from app.schemas import (
    ArticleResponse,
    ArticleIndexResponse,
    ArticleSearchResponse,
    AuthorProfileResponse,
    CorrectionCreate,
    CorrectionResponse,
    LiveUpdateCreate,
    LiveUpdateResponse,
    NewsletterSubscribe,
    NewsroomMessageCreate,
    NewsroomMessageResponse,
)


router = APIRouter(tags=["Public Publication Services"])


def article_filters(
    q: Optional[str] = None,
    category: Optional[str] = None,
    author: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    article_type: Optional[str] = None,
    breaking_only: bool = False,
):
    filters = [Article.status == "PUBLISHED"]
    if q and q.strip():
        search = f"%{q.strip()}%"
        filters.append(or_(
            Article.title.ilike(search),
            Article.subtitle.ilike(search),
            Article.summary.ilike(search),
            Article.content.ilike(search),
            Article.tags.ilike(search),
        ))
    if category and category.lower() != "all":
        filters.append(func.lower(Article.category) == category.strip().lower())
    if author:
        normalized = author.strip().lower()
        filters.append(Article.author.has(or_(
            func.lower(User.username) == normalized,
            func.lower(User.slug) == normalized,
        )))
    if date_from:
        filters.append(func.coalesce(Article.published_at, Article.created_at) >= date_from)
    if date_to:
        filters.append(func.coalesce(Article.published_at, Article.created_at) <= date_to)
    if article_type:
        filters.append(func.lower(Article.article_type) == article_type.strip().lower())
    if breaking_only:
        filters.append(Article.is_breaking == True)
    return filters


def article_order(sort: str, q: Optional[str] = None):
    published = func.coalesce(Article.published_at, Article.created_at)
    if sort == "oldest":
        return [published.asc(), Article.id.asc()]
    if sort == "most_read":
        return [Article.view_count.desc(), published.desc()]
    if sort == "relevance" and q and q.strip():
        search = f"%{q.strip()}%"
        return [case((Article.title.ilike(search), 0), else_=1), published.desc()]
    return [published.desc(), Article.id.desc()]


@router.get("/api/articles/search", response_model=ArticleSearchResponse)
async def search_articles(
    q: Optional[str] = None,
    category: Optional[str] = None,
    author: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    article_type: Optional[str] = None,
    breaking_only: bool = False,
    sort: Literal["newest", "oldest", "most_read", "relevance"] = "newest",
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Search published stories with newsroom-grade filters and pagination."""
    filters = article_filters(q, category, author, date_from, date_to, article_type, breaking_only)
    total = (await db.execute(select(func.count(Article.id)).filter(*filters))).scalar() or 0
    query = (
        select(Article)
        .filter(*filters)
        .options(selectinload(Article.author), selectinload(Article.editor))
        .order_by(*article_order(sort, q))
        .offset(offset)
        .limit(limit)
    )
    items = (await db.execute(query)).scalars().all()
    suggestions = [article.title for article in items[:5]] if q and q.strip() else []
    return ArticleSearchResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        suggestions=suggestions,
    )


@router.get("/api/articles/index", response_model=list[ArticleIndexResponse])
async def publication_index(
    limit: int = Query(default=1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Compact publication index used by archive and sitemap generation."""
    query = (
        select(Article)
        .filter(Article.status == "PUBLISHED")
        .options(selectinload(Article.author), selectinload(Article.editor))
        .order_by(func.coalesce(Article.published_at, Article.created_at).desc())
        .limit(limit)
    )
    return (await db.execute(query)).scalars().all()


@router.get("/api/articles/most-read", response_model=list[ArticleResponse])
async def most_read_articles(
    limit: int = Query(default=8, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Article)
        .filter(Article.status == "PUBLISHED")
        .options(selectinload(Article.author), selectinload(Article.editor))
        .order_by(Article.view_count.desc(), Article.published_at.desc())
        .limit(limit)
    )
    return (await db.execute(query)).scalars().all()


@router.get("/api/authors/{slug}", response_model=AuthorProfileResponse)
async def author_profile(
    slug: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    normalized = slug.strip().lower()
    author = (await db.execute(select(User).filter(or_(
        func.lower(User.slug) == normalized,
        func.lower(User.username) == normalized,
    )))).scalars().first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    filters = [Article.author_id == author.id, Article.status == "PUBLISHED"]
    total_articles = (await db.execute(select(func.count(Article.id)).filter(*filters))).scalar() or 0
    total_views = (await db.execute(select(func.coalesce(func.sum(Article.view_count), 0)).filter(*filters))).scalar() or 0
    articles = (await db.execute(
        select(Article)
        .filter(*filters)
        .options(selectinload(Article.author), selectinload(Article.editor))
        .order_by(func.coalesce(Article.published_at, Article.created_at).desc())
        .limit(limit)
    )).scalars().all()

    configured = [item.strip() for item in (author.coverage_areas or "").split(",") if item.strip()]
    observed = [article.category for article in articles if article.category]
    coverage = list(dict.fromkeys([*configured, *observed]))
    return AuthorProfileResponse(
        author=author,
        articles=articles,
        total_articles=total_articles,
        total_views=total_views,
        coverage_areas=coverage,
    )


def correction_payload(correction: Correction) -> CorrectionResponse:
    return CorrectionResponse(
        id=correction.id,
        article_id=correction.article_id,
        summary=correction.summary,
        details=correction.details,
        created_at=correction.created_at,
        article_title=correction.article.title,
        article_slug=correction.article.slug,
        recorded_by=correction.recorded_by.username,
    )


@router.get("/api/corrections", response_model=list[CorrectionResponse])
async def list_corrections(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Correction)
        .join(Correction.article)
        .filter(Article.status == "PUBLISHED")
        .options(selectinload(Correction.article), selectinload(Correction.recorded_by))
        .order_by(Correction.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return [correction_payload(row) for row in rows]


@router.post("/api/corrections", response_model=CorrectionResponse, status_code=status.HTTP_201_CREATED)
async def create_correction(
    payload: CorrectionCreate,
    current_user: User = Depends(require_role(["EDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    article = (await db.execute(select(Article).filter(Article.id == payload.article_id))).scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    correction = Correction(
        article_id=article.id,
        summary=payload.summary.strip(),
        details=payload.details.strip() if payload.details else None,
        recorded_by_id=current_user.id,
    )
    db.add(correction)
    if article.author_id != current_user.id:
        db.add(Notification(
            user_id=article.author_id,
            message=f"A correction was recorded for '{article.title}'.",
            type="INFO",
            link=f"/articles/{article.slug}",
        ))
    await db.commit()
    row = (await db.execute(
        select(Correction)
        .filter(Correction.id == correction.id)
        .options(selectinload(Correction.article), selectinload(Correction.recorded_by))
    )).scalars().first()
    return correction_payload(row)


@router.post("/api/newsletter/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_newsletter(
    payload: NewsletterSubscribe,
    db: AsyncSession = Depends(get_db),
):
    subscriber = (await db.execute(
        select(NewsletterSubscriber).filter(func.lower(NewsletterSubscriber.email) == payload.email)
    )).scalars().first()
    if subscriber:
        subscriber.is_active = True
        subscriber.source = payload.source
        db.add(subscriber)
        await db.commit()
        return {"status": "subscribed", "message": "This address is subscribed to the newsletter."}
    db.add(NewsletterSubscriber(email=payload.email, source=payload.source))
    await db.commit()
    return {"status": "subscribed", "message": "Newsletter subscription saved."}


@router.post("/api/newsroom/messages", response_model=NewsroomMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_newsroom_message(
    payload: NewsroomMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Accept a clearly non-anonymous newsroom enquiry without inventing email infrastructure."""
    message = NewsroomMessage(
        purpose=payload.purpose,
        name=payload.name,
        email=payload.email,
        message=payload.message.strip(),
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


@router.get("/api/newsroom/messages", response_model=list[NewsroomMessageResponse])
async def list_newsroom_messages(
    purpose: Optional[str] = None,
    current_user: User = Depends(require_role(["EDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(NewsroomMessage)
    if purpose:
        query = query.filter(NewsroomMessage.purpose == purpose.strip().lower())
    return (await db.execute(query.order_by(NewsroomMessage.created_at.desc()).limit(500))).scalars().all()


@router.get("/api/live/{slug}", response_model=list[LiveUpdateResponse])
async def list_live_updates(slug: str, db: AsyncSession = Depends(get_db)):
    article = (await db.execute(select(Article).filter(
        Article.slug == slug,
        Article.status == "PUBLISHED",
        Article.article_type == "LIVE",
    ))).scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Live coverage not found")
    return (await db.execute(
        select(LiveUpdate)
        .filter(LiveUpdate.article_id == article.id)
        .options(selectinload(LiveUpdate.author))
        .order_by(LiveUpdate.created_at.desc())
    )).scalars().all()


@router.post("/api/live/{article_id}/updates", response_model=LiveUpdateResponse, status_code=status.HTTP_201_CREATED)
async def create_live_update(
    article_id: int,
    payload: LiveUpdateCreate,
    current_user: User = Depends(require_role(["EDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    article = (await db.execute(select(Article).filter(Article.id == article_id))).scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.article_type != "LIVE":
        raise HTTPException(status_code=400, detail="Article is not configured for live coverage")
    update = LiveUpdate(article_id=article.id, author_id=current_user.id, content=sanitize_article_html(payload.content.strip()))
    article.updated_at = utc_now()
    db.add_all([update, article])
    await db.commit()
    return (await db.execute(
        select(LiveUpdate).filter(LiveUpdate.id == update.id).options(selectinload(LiveUpdate.author))
    )).scalars().first()
