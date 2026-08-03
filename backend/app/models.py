from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="READER", nullable=False)    # READER, JOURNALIST, EDITOR, ADMIN, SUPER_ADMIN
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    articles_written = relationship("Article", back_populates="author", foreign_keys="[Article.author_id]")
    articles_edited = relationship("Article", back_populates="editor", foreign_keys="[Article.editor_id]")
    comments = relationship("Comment", back_populates="author")
    reviews = relationship("ReviewComment", back_populates="author")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(String, default="DRAFT", nullable=False)  # DRAFT, SUBMITTED, PUBLISHED, REJECTED
    category = Column(String, default="General", nullable=False)
    image_url = Column(String, nullable=True)
    image_caption = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # comma-separated
    view_count = Column(Integer, default=0, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_breaking = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    published_at = Column(DateTime, nullable=True)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    editor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    author = relationship("User", back_populates="articles_written", foreign_keys=[author_id])
    editor = relationship("User", back_populates="articles_edited", foreign_keys=[editor_id])
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")
    reviews = relationship("ReviewComment", back_populates="article", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    article = relationship("Article", back_populates="comments")
    author = relationship("User", back_populates="comments")


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    article = relationship("Article", back_populates="reviews")
    author = relationship("User", back_populates="reviews")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="INFO", nullable=False)  # INFO, SUCCESS, WARNING, ALERT
    is_read = Column(Boolean, default=False, nullable=False)
    link = Column(String, nullable=True)  # Optional deeplink URL
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")


class SiteSetting(Base):
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
