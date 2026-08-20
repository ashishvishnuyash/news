from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import re
from app.content import sanitize_article_html

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
ROLES = {"READER", "JOURNALIST", "EDITOR", "ADMIN", "SUPER_ADMIN"}
ARTICLE_STATUSES = {
    "DRAFT", "FACT_CHECK", "EDITOR_REVIEW", "APPROVED", "SCHEDULED",
    "PUBLISHED", "REJECTED", "SUBMITTED",  # SUBMITTED remains for legacy clients.
}
ARTICLE_TYPES = {"NEWS", "OPINION", "INVESTIGATION", "FACT_CHECK", "LIVE"}
FACT_CHECK_RATINGS = {"TRUE", "FALSE", "PARTLY_TRUE", "MISLEADING", "UNVERIFIED"}


# ──────────────────────────────────────────────────────────────
# Auth / Token
# ──────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# User
# ──────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    username: str

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("Username must be 3–40 letters, numbers, dots, dashes, or underscores")
        return value


class UserCreate(UserBase):
    """Used for login (username + password only)."""
    password: str = Field(min_length=8, max_length=128)


class UserRegister(UserBase):
    """Used for registration (username, email, password, confirm)."""
    email: Optional[str] = Field(default=None, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_password != self.password:
            raise ValueError("Passwords do not match")
        if self.email:
            self.email = self.email.strip().lower()
            if "@" not in self.email:
                raise ValueError("Enter a valid email address")
        return self


class UserProfileUpdate(BaseModel):
    email: Optional[str] = Field(default=None, max_length=254)
    bio: Optional[str] = Field(default=None, max_length=1200)
    profile_image_url: Optional[str] = Field(default=None, max_length=2000)
    job_title: Optional[str] = Field(default=None, max_length=120)
    coverage_areas: Optional[str] = Field(default=None, max_length=500)
    social_links: Optional[str] = Field(default=None, max_length=4000)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_new_password != self.new_password:
            raise ValueError("New passwords do not match")
        return self


class UserUpdateRole(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        value = value.upper()
        if value not in ROLES:
            raise ValueError("Invalid role")
        return value


class AdminUserCreate(UserBase):
    email: Optional[str] = Field(default=None, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    role: str = "READER"
    bio: Optional[str] = Field(default=None, max_length=1200)
    profile_image_url: Optional[str] = Field(default=None, max_length=2000)
    job_title: Optional[str] = Field(default=None, max_length=120)
    coverage_areas: Optional[str] = Field(default=None, max_length=500)
    social_links: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        value = value.upper()
        if value not in ROLES:
            raise ValueError("Invalid role")
        return value


class AdminUserUpdate(BaseModel):
    email: Optional[str] = Field(default=None, max_length=254)
    bio: Optional[str] = Field(default=None, max_length=1200)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    profile_image_url: Optional[str] = Field(default=None, max_length=2000)
    job_title: Optional[str] = Field(default=None, max_length=120)
    coverage_areas: Optional[str] = Field(default=None, max_length=500)
    social_links: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.upper()
        if value not in ROLES:
            raise ValueError("Invalid role")
        return value


class UserResponse(UserBase):
    id: int
    role: str
    email: Optional[str] = None
    bio: Optional[str] = None
    slug: Optional[str] = None
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    coverage_areas: Optional[str] = None
    social_links: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicAuthorResponse(BaseModel):
    """Public byline identity; deliberately excludes account email and state."""
    id: int
    username: str
    role: str
    bio: Optional[str] = None
    slug: Optional[str] = None
    profile_image_url: Optional[str] = None
    job_title: Optional[str] = None
    coverage_areas: Optional[str] = None
    social_links: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────
# Notification
# ──────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: int
    message: str
    type: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────
# Comment
# ──────────────────────────────────────────────────────────────

class CommentBase(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Comment cannot be empty")
        return value


class CommentCreate(CommentBase):
    pass


class CommentUpdate(CommentBase):
    pass


class CommentResponse(CommentBase):
    id: int
    article_id: int
    author: PublicAuthorResponse
    created_at: datetime
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────
# ReviewComment
# ──────────────────────────────────────────────────────────────

class ReviewCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ReviewCommentResponse(BaseModel):
    id: int
    article_id: int
    author: PublicAuthorResponse
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────
# Article
# ──────────────────────────────────────────────────────────────

class ArticleBase(BaseModel):
    title: str = Field(min_length=5, max_length=220)
    slug: Optional[str] = Field(default=None, min_length=3, max_length=240)
    author_id: Optional[int] = None
    subtitle: Optional[str] = Field(default=None, max_length=500)
    content: str = Field(min_length=20, max_length=200_000)
    summary: Optional[str] = Field(default=None, max_length=800)
    category: str = Field(default="General", min_length=2, max_length=80)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    image_caption: Optional[str] = Field(default=None, max_length=300)
    tags: Optional[str] = Field(default=None, max_length=500)
    sources: Optional[str] = Field(default=None, max_length=20_000)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=170)
    og_image_url: Optional[str] = Field(default=None, max_length=2000)
    article_type: str = "NEWS"
    fact_check_rating: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    is_pinned: bool = False
    is_breaking: bool = False

    @field_validator("title", "category")
    @classmethod
    def clean_short_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("content")
    @classmethod
    def safe_article_content(cls, value: str) -> str:
        clean = sanitize_article_html(value)
        if len(clean) < 20:
            raise ValueError("Article content is too short")
        return clean

    @field_validator("article_type")
    @classmethod
    def valid_article_type(cls, value: str) -> str:
        value = value.upper()
        if value not in ARTICLE_TYPES:
            raise ValueError("Invalid article type")
        return value

    @field_validator("fact_check_rating")
    @classmethod
    def valid_fact_check_rating(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        value = value.upper().replace(" ", "_")
        if value not in FACT_CHECK_RATINGS:
            raise ValueError("Invalid fact-check rating")
        return value


class ArticleCreate(ArticleBase):
    summary: str = Field(min_length=10, max_length=800)

    @field_validator("summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Summary must be at least 10 characters")
        return value

    @model_validator(mode="after")
    def caption_requires_image(self):
        if self.image_caption and not self.image_url:
            raise ValueError("Add an image before adding an image caption")
        return self


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=220)
    slug: Optional[str] = Field(default=None, min_length=3, max_length=240)
    author_id: Optional[int] = None
    subtitle: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = Field(default=None, min_length=20, max_length=200_000)
    summary: Optional[str] = Field(default=None, min_length=10, max_length=800)
    category: Optional[str] = Field(default=None, min_length=2, max_length=80)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    image_caption: Optional[str] = Field(default=None, max_length=300)
    tags: Optional[str] = Field(default=None, max_length=500)
    sources: Optional[str] = Field(default=None, max_length=20_000)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=170)
    og_image_url: Optional[str] = Field(default=None, max_length=2000)
    article_type: Optional[str] = None
    fact_check_rating: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None  # DRAFT, SUBMITTED, PUBLISHED, REJECTED
    is_pinned: Optional[bool] = None
    is_breaking: Optional[bool] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.upper()
        if value not in ARTICLE_STATUSES:
            raise ValueError("Invalid article status")
        return value

    @field_validator("article_type")
    @classmethod
    def valid_article_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.upper()
        if value not in ARTICLE_TYPES:
            raise ValueError("Invalid article type")
        return value

    @field_validator("fact_check_rating")
    @classmethod
    def valid_fact_check_rating(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        value = value.upper().replace(" ", "_")
        if value not in FACT_CHECK_RATINGS:
            raise ValueError("Invalid fact-check rating")
        return value


class ArticleResponse(BaseModel):
    """Article data returned from storage.

    Response models intentionally do not inherit the create-time length
    constraints. Older/imported rows can contain incomplete draft content and
    must remain visible to staff so they can be repaired instead of causing an
    entire listing endpoint to fail response validation.
    """

    id: int
    title: str
    subtitle: Optional[str] = None
    content: str
    summary: Optional[str] = None
    category: str = "General"
    image_url: Optional[str] = None
    image_caption: Optional[str] = None
    tags: Optional[str] = None
    sources: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_image_url: Optional[str] = None
    article_type: str = "NEWS"
    fact_check_rating: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    is_pinned: bool = False
    is_breaking: bool = False
    slug: Optional[str] = None
    status: str
    view_count: int = 0
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    author: PublicAuthorResponse
    editor: Optional[PublicAuthorResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────
# Site Settings & Admin Stats
# ──────────────────────────────────────────────────────────────

class SiteSettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class SiteSettingCreate(SiteSettingBase):
    pass


class SiteSettingResponse(SiteSettingBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SiteSettingsBatchUpdate(BaseModel):
    settings: List[SiteSettingBase]


class AdminStats(BaseModel):
    total_users: int
    total_articles: int
    published_articles: int
    draft_articles: int
    submitted_articles: int
    rejected_articles: int
    fact_check_articles: int = 0
    editor_review_articles: int = 0
    approved_articles: int = 0
    scheduled_articles: int = 0
    total_corrections: int = 0
    total_comments: int
    total_journalists: int
    total_editors: int
    total_readers: int
    total_superadmins: int = 0


class ArticleSearchResponse(BaseModel):
    items: List[ArticleResponse]
    total: int
    limit: int
    offset: int
    suggestions: List[str] = Field(default_factory=list)


class ArticleIndexResponse(BaseModel):
    """Compact public record used by archives and sitemap generation."""
    id: int
    slug: Optional[str] = None
    title: str
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    category: str
    image_url: Optional[str] = None
    image_caption: Optional[str] = None
    tags: Optional[str] = None
    article_type: str = "NEWS"
    fact_check_rating: Optional[str] = None
    view_count: int = 0
    is_pinned: bool = False
    is_breaking: bool = False
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    author: PublicAuthorResponse

    model_config = ConfigDict(from_attributes=True)


class AuthorProfileResponse(BaseModel):
    author: PublicAuthorResponse
    articles: List[ArticleResponse]
    total_articles: int
    total_views: int
    coverage_areas: List[str] = Field(default_factory=list)


class CorrectionCreate(BaseModel):
    article_id: int
    summary: str = Field(min_length=5, max_length=500)
    details: Optional[str] = Field(default=None, max_length=5000)


class CorrectionResponse(BaseModel):
    id: int
    article_id: int
    summary: str
    details: Optional[str] = None
    created_at: datetime
    article_title: str
    article_slug: Optional[str] = None
    recorded_by: str


class NewsletterSubscribe(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    source: str = Field(default="website", max_length=80)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address")
        return value


class LiveUpdateCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class LiveUpdateResponse(BaseModel):
    id: int
    article_id: int
    content: str
    created_at: datetime
    updated_at: datetime
    author: PublicAuthorResponse

    model_config = ConfigDict(from_attributes=True)


class NewsroomMessageCreate(BaseModel):
    purpose: str = Field(max_length=30)
    name: Optional[str] = Field(default=None, max_length=120)
    email: Optional[str] = Field(default=None, max_length=254)
    message: str = Field(min_length=20, max_length=10_000)

    @field_validator("purpose")
    @classmethod
    def valid_purpose(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"general", "tips", "corrections", "advertising", "press"}:
            raise ValueError("Choose a valid contact purpose")
        return value

    @field_validator("name", "email")
    @classmethod
    def clean_optional(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() or None if value is not None else None

    @field_validator("email")
    @classmethod
    def valid_optional_email(cls, value: Optional[str]) -> Optional[str]:
        if value and ("@" not in value or value.startswith("@") or value.endswith("@")):
            raise ValueError("Enter a valid email address")
        return value.lower() if value else value


class NewsroomMessageResponse(BaseModel):
    id: int
    purpose: str
    name: Optional[str] = None
    email: Optional[str] = None
    message: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
