from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Comment, ReviewComment, Article, User
from app.schemas import CommentCreate, CommentResponse, CommentUpdate, ReviewCommentCreate, ReviewCommentResponse
from app.auth import get_current_user, require_role
from app.site_config import feature_enabled

router = APIRouter(prefix="/api/articles", tags=["Comments"])

# 1. Reader Comments (Public)

@router.get("/{slug_or_id}/comments", response_model=List[CommentResponse])
async def list_comments(slug_or_id: str, db: AsyncSession = Depends(get_db)):
    if slug_or_id.isdigit():
        art_result = await db.execute(select(Article).filter(Article.id == int(slug_or_id)))
    else:
        art_result = await db.execute(select(Article).filter(Article.slug == slug_or_id))
    article = art_result.scalars().first()
    if not article or article.status != "PUBLISHED":
        raise HTTPException(status_code=404, detail="Article not found")
        
    query = select(Comment).filter(Comment.article_id == article.id, Comment.is_deleted == False).options(
        selectinload(Comment.author)
    ).order_by(Comment.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/{slug_or_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    slug_or_id: str,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not await feature_enabled(db, "comments_enabled", True):
        raise HTTPException(status_code=403, detail="Reader comments are currently closed.")
    if slug_or_id.isdigit():
        art_result = await db.execute(select(Article).filter(Article.id == int(slug_or_id)))
    else:
        art_result = await db.execute(select(Article).filter(Article.slug == slug_or_id))
    article = art_result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if article.status != "PUBLISHED":
        raise HTTPException(status_code=403, detail="Cannot comment on unpublished articles")
        
    db_comment = Comment(
        content=comment_in.content,
        article_id=article.id,
        author_id=current_user.id
    )
    db.add(db_comment)
    await db.commit()
    
    # Reload to populate author relationship
    res = await db.execute(
        select(Comment)
        .filter(Comment.id == db_comment.id)
        .options(selectinload(Comment.author))
    )
    return res.scalars().first()


@router.put("/{slug_or_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    slug_or_id: str,
    comment_id: int,
    payload: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if slug_or_id.isdigit():
        article_filter = Article.id == int(slug_or_id)
    else:
        article_filter = Article.slug == slug_or_id
    article = (await db.execute(select(Article).filter(article_filter))).scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    comment = (await db.execute(
        select(Comment)
        .filter(Comment.id == comment_id, Comment.article_id == article.id, Comment.is_deleted == False)
        .options(selectinload(Comment.author))
    )).scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="You can only edit your own response")
    comment.content = payload.content
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.delete("/{slug_or_id}/comments/{comment_id}")
async def delete_comment(
    slug_or_id: str,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if slug_or_id.isdigit():
        article_filter = Article.id == int(slug_or_id)
    else:
        article_filter = Article.slug == slug_or_id
    article = (await db.execute(select(Article).filter(article_filter))).scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    comment = (await db.execute(
        select(Comment).filter(
            Comment.id == comment_id,
            Comment.article_id == article.id,
            Comment.is_deleted == False,
        )
    )).scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="You can only delete your own response")
    comment.is_deleted = True
    db.add(comment)
    await db.commit()
    return {"status": "success", "message": "Response deleted"}


# 2. Editorial Review Comments (Internal between Journalist & Editor)

@router.get("/{slug_or_id}/reviews", response_model=List[ReviewCommentResponse])
async def list_reviews(
    slug_or_id: str,
    current_user: User = Depends(require_role(["JOURNALIST", "EDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    if slug_or_id.isdigit():
        art_result = await db.execute(select(Article).filter(Article.id == int(slug_or_id)))
    else:
        art_result = await db.execute(select(Article).filter(Article.slug == slug_or_id))
    article = art_result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    # Journalists can only view review comments on their own articles
    if current_user.role == "JOURNALIST" and article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view reviews for this article")
        
    query = select(ReviewComment).filter(ReviewComment.article_id == article.id).options(
        selectinload(ReviewComment.author)
    ).order_by(ReviewComment.created_at.asc())
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/{slug_or_id}/reviews", response_model=ReviewCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    slug_or_id: str,
    review_in: ReviewCommentCreate,
    current_user: User = Depends(require_role(["JOURNALIST", "EDITOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    if slug_or_id.isdigit():
        art_result = await db.execute(select(Article).filter(Article.id == int(slug_or_id)))
    else:
        art_result = await db.execute(select(Article).filter(Article.slug == slug_or_id))
    article = art_result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    # Journalists can only add review comments on their own articles
    if current_user.role == "JOURNALIST" and article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to comment on this review")
        
    db_review = ReviewComment(
        content=review_in.content,
        article_id=article.id,
        author_id=current_user.id
    )
    db.add(db_review)
    await db.commit()
    
    # Reload
    res = await db.execute(
        select(ReviewComment)
        .filter(ReviewComment.id == db_review.id)
        .options(selectinload(ReviewComment.author))
    )
    return res.scalars().first()
