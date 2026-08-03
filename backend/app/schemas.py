from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import re
from app.content import sanitize_article_html

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
ROLES = {"READER", "JOURNALIST", "EDITOR", "ADMIN", "SUPER_ADMIN"}
ARTICLE_STATUSES = {"DRAFT", "SUBMITTED", "PUBLISHED", "REJECTED"}


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
    is_active: bool = True
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
    author: UserResponse
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
    author: UserResponse
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────
# Article
# ──────────────────────────────────────────────────────────────

class ArticleBase(BaseModel):
    title: str = Field(min_length=5, max_length=220)
    content: str = Field(min_length=20, max_length=200_000)
    summary: Optional[str] = Field(default=None, max_length=800)
    category: str = Field(default="General", min_length=2, max_length=80)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    image_caption: Optional[str] = Field(default=None, max_length=300)
    tags: Optional[str] = Field(default=None, max_length=500)
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
    content: Optional[str] = Field(default=None, min_length=20, max_length=200_000)
    summary: Optional[str] = Field(default=None, min_length=10, max_length=800)
    category: Optional[str] = Field(default=None, min_length=2, max_length=80)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    image_caption: Optional[str] = Field(default=None, max_length=300)
    tags: Optional[str] = Field(default=None, max_length=500)
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


class ArticleResponse(ArticleBase):
    id: int
    slug: Optional[str] = None
    status: str
    view_count: int = 0
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    author: UserResponse
    editor: Optional[UserResponse] = None

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
    total_comments: int
    total_journalists: int
    total_editors: int
    total_readers: int
    total_superadmins: int = 0
