from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="READER", nullable=False)    # READER, JOURNALIST, EDITOR, ADMIN, SUPER_ADMIN
    bio = Column(Text, nullable=True)
    slug = Column(String, nullable=True, index=True)
    profile_image_url = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    coverage_areas = Column(Text, nullable=True)
    social_links = Column(Text, nullable=True)
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
    subtitle = Column(Text, nullable=True)
    slug = Column(String, unique=True, index=True, nullable=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(String, default="DRAFT", nullable=False)  # DRAFT, SUBMITTED, PUBLISHED, REJECTED
    category = Column(String, default="General", nullable=False)
    image_url = Column(String, nullable=True)
    image_caption = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # comma-separated
    sources = Column(Text, nullable=True)
    seo_title = Column(String, nullable=True)
    seo_description = Column(Text, nullable=True)
    og_image_url = Column(String, nullable=True)
    article_type = Column(String, default="NEWS", nullable=False)  # NEWS, OPINION, INVESTIGATION, FACT_CHECK, LIVE
    fact_check_rating = Column(String, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
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
    corrections = relationship("Correction", back_populates="article", cascade="all, delete-orphan")
    live_updates = relationship("LiveUpdate", back_populates="article", cascade="all, delete-orphan")


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


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    summary = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    article = relationship("Article", back_populates="corrections")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, default="website", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class LiveUpdate(Base):
    __tablename__ = "live_updates"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    article = relationship("Article", back_populates="live_updates")
    author = relationship("User", foreign_keys=[author_id])


class NewsroomMessage(Base):
    __tablename__ = "newsroom_messages"

    id = Column(Integer, primary_key=True, index=True)
    purpose = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String, default="NEW", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
