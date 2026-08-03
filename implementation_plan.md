# Implementation Plan - Vintage Newspaper Platform

This plan outlines the design and implementation of a responsive, black-and-white vintage newspaper web application. The platform features an App Router-based Next.js frontend with subdomain routing for different panels, and a FastAPI backend with a SQLite database using SQLAlchemy.

---

## User Review Required

> [!IMPORTANT]
> **Subdomain Local Development Setup:**
> - To support subdomains locally (e.g., `journalist.localhost:3000`, `editor.localhost:3000`, `admin.localhost:3000`), modern browsers (Chrome and Firefox) resolve `*.localhost` to `127.0.0.1` automatically without needing to edit the system `hosts` file.
> - For Safari or other environments, a hosts file update or local DNS proxy (e.g., dnsmasq) might be required. We will use standard `*.localhost` as the default approach.

> [!TIP]
> **Vintage Design System (Black & White Newspaper CSS):**
> - Background: Aged paper off-white (`#F6F3EB`) and ink black (`#1C1A17`) for light mode; aged charcoal (`#121212`) and soft white (`#E5E0D8`) for dark mode.
> - Typography: Serif fonts (e.g., Playfair Display, Georgia) for headers, slab-serif or sans-serif for body copy, monospace (Courier) for editorial metadata.
> - Newspaper Layout: CSS Columns and CSS Grid to mimic newspaper columns, double-rule borders, drop caps, and a rustic masthead.
> - Media: CSS filters to render all uploaded images in grayscale/sepia with high contrast, mimicking newsprint halftone images.

---

## Open Questions

*None at this stage, as tech stack decisions (Next.js App Router, TypeScript, CSS Modules, FastAPI, SQLite, SQLAlchemy, unified cookie-based auth) have been resolved during the grill-me phase.*

---

## Proposed Changes

We will create two main directories in the workspace: `frontend/` and `backend/`.

```
d:\NeWS\
├── frontend/             # Next.js App Router application
└── backend/              # FastAPI python application
```

---

### Backend (FastAPI + SQLAlchemy + SQLite)

A Python FastAPI application providing authentication, article management, comments, and role checks.

#### [NEW] [main.py](file:///d:/NeWS/backend/app/main.py)
- Entry point of the FastAPI application.
- Configures CORS (allowing subdomains) and includes API routers.

#### [NEW] [config.py](file:///d:/NeWS/backend/app/config.py)
- Environment and app configurations (Secret keys, JWT algorithm, SQLite file path).

#### [NEW] [database.py](file:///d:/NeWS/backend/app/database.py)
- Setup SQLAlchemy async engine and session maker using `sqlite+aiosqlite`.
- Base model declaration.

#### [NEW] [models.py](file:///d:/NeWS/backend/app/models.py)
- **User**: `id`, `username`, `hashed_password`, `role` (READER, JOURNALIST, EDITOR, ADMIN), `created_at`.
- **Article**: `id`, `title`, `content`, `summary`, `status` (`DRAFT`, `SUBMITTED`, `PUBLISHED`, `REJECTED`), `author_id` (foreign key to User), `editor_id` (foreign key to User, nullable), `published_at`, `category`, `image_url` (nullable), `created_at`, `updated_at`.
- **Comment**: `id`, `content`, `article_id` (foreign key), `author_id` (foreign key), `created_at`.
- **ReviewComment**: `id`, `content`, `article_id` (foreign key), `author_id` (foreign key), `created_at` (internal review logs for journalists & editors).

#### [NEW] [schemas.py](file:///d:/NeWS/backend/app/schemas.py)
- Pydantic models for request/response serialization (Auth, Article, Comment, User).

#### [NEW] [auth.py](file:///d:/NeWS/backend/app/auth.py)
- Password hashing using `passlib` (bcrypt).
- JWT token generation and validation.
- FastAPI dependencies for getting current user and verifying roles.

#### [NEW] [router_auth.py](file:///d:/NeWS/backend/app/routers/auth.py)
- Endpoints:
  - `POST /api/auth/register` (register new reader/user)
  - `POST /api/auth/login` (verifies credentials, sets HttpOnly JWT cookie with domain `.localhost`)
  - `POST /api/auth/logout` (clears the JWT cookie)
  - `GET /api/auth/me` (returns current user profile and role)

#### [NEW] [router_articles.py](file:///d:/NeWS/backend/app/routers/articles.py)
- Endpoints:
  - `GET /api/articles` (public published articles)
  - `GET /api/articles/{id}` (get article details)
  - `POST /api/articles` (Journalist: create a draft)
  - `PUT /api/articles/{id}` (Journalist/Editor: update draft, submit, publish, or reject)
  - `GET /api/articles/editor/queue` (Editor: get all articles submitted for review)
  - `GET /api/articles/journalist/my` (Journalist: get own drafts/articles)

#### [NEW] [router_comments.py](file:///d:/NeWS/backend/app/routers/comments.py)
- Endpoints:
  - `GET /api/articles/{id}/comments` (get comments)
  - `POST /api/articles/{id}/comments` (add comment)
  - `GET /api/articles/{id}/reviews` (get editor-journalist reviews)
  - `POST /api/articles/{id}/reviews` (add editor-journalist review comment)

#### [NEW] [router_admin.py](file:///d:/NeWS/backend/app/routers/admin.py)
- Endpoints:
  - `GET /api/admin/users` (list users)
  - `PUT /api/admin/users/{id}/role` (change user role)

---

### Frontend (Next.js App Router + TypeScript + CSS Modules)

A Next.js frontend with subdomain middleware routing.

#### [NEW] [middleware.ts](file:///d:/NeWS/frontend/src/middleware.ts)
- Next.js middleware that checks the incoming `host` header.
- If the host matches `<subdomain>.localhost:3000`, rewrite the URL internally to `/panels/<subdomain>/:path*`.
- Handles subdomains: `journalist`, `editor`, `admin`.
- Passes the root domain (`localhost:3000`) through to reader pages.

#### [NEW] [next.config.js](file:///d:/NeWS/frontend/next.config.js)
- Configuration to allow cors and routing correctly.

#### [NEW] [global.css](file:///d:/NeWS/frontend/src/app/globals.css)
- Custom typography (import Google Fonts: Playfair Display, Outfit).
- Color tokens for the old newspaper theme.
- Vintage page animations and halftone/grayscale filters.

#### [NEW] Reader Layout & Pages (Root Domain)
- [layout.tsx](file:///d:/NeWS/frontend/src/app/(reader)/layout.tsx): Vintage header masthead, navigation, and paper border lines.
- [page.tsx](file:///d:/NeWS/frontend/src/app/(reader)/page.tsx): Main homepage, layout like a front page with column layout, featured articles, and sidebars.
- [articles/[id]/page.tsx](file:///d:/NeWS/frontend/src/app/(reader)/articles/%5Bid%5D/page.tsx): Article reader view with drop cap, clean newspaper paragraph layout, and comment section.
- [login/page.tsx](file:///d:/NeWS/frontend/src/app/(reader)/login/page.tsx): Unified login page that redirects users to their dashboard subdomains if they are not reader-only.
- [register/page.tsx](file:///d:/NeWS/frontend/src/app/(reader)/register/page.tsx): Reader registration.

#### [NEW] Subdomain Panels (Internally Rewritten via Middleware)
- [panels/journalist/page.tsx](file:///d:/NeWS/frontend/src/app/panels/journalist/page.tsx): Journalist dashboard (write new draft, list my drafts/articles, edit drafts).
- [panels/editor/page.tsx](file:///d:/NeWS/frontend/src/app/panels/editor/page.tsx): Editor dashboard (view editorial queue, read drafts, approve/publish, reject/add comments).
- [panels/admin/page.tsx](file:///d:/NeWS/frontend/src/app/panels/admin/page.tsx): Admin dashboard (list users, manage user roles).
- [panels/layout.tsx](file:///d:/NeWS/frontend/src/app/panels/layout.tsx): Shared panel shell with user authorization verification (validates if user has required role, otherwise redirects to login).

---

## Verification Plan

### Automated Tests
- We will write a test/validation script `verify_backend.py` inside `backend/` using `pytest` or `httpx` to verify authentication, role enforcement, and article states.

### Manual Verification
- Start FastAPI backend on `http://localhost:8000`.
- Start Next.js frontend on `http://localhost:3000`.
- Access different pages:
  - `http://localhost:3000/` (Reader homepage)
  - `http://journalist.localhost:3000/` (Journalist dashboard)
  - `http://editor.localhost:3000/` (Editor dashboard)
  - `http://admin.localhost:3000/` (Admin dashboard)
- Test signup, login, dashboard redirection, draft submission, editor approval/publishing, and reader comments.
