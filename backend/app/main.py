from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.config import settings as config_settings
from app.database import engine, Base
from app.routers import auth, articles, comments, admin, media, users, settings as settings_router


MEDIA_DIRECTORY = Path(__file__).resolve().parents[1] / "uploads"
MEDIA_DIRECTORY.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config_settings.ENVIRONMENT.lower() == "production" and config_settings.SECRET_KEY.startswith("supersecret"):
        raise RuntimeError("SECRET_KEY must be set to a strong private value in production")
    # Automatically create / migrate tables on startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"⚠️ Warning: Database connection failed during startup ({e}). Ensure DB host is reachable.")
    yield



app = FastAPI(
    title="The Republic Bulletin API",
    description="Production-ready backend API for The Republic Bulletin vintage news platform.",
    version="2.5.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — allow localhost main + all subdomains on port 3000/3001
app.add_middleware(
    CORSMiddleware,
    allow_origins=config_settings.cors_origins,
    allow_origin_regex=config_settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=config_settings.allowed_hosts)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIRECTORY)), name="media")

# Register all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(media.router)
app.include_router(articles.router)
app.include_router(comments.router)
app.include_router(admin.router)
app.include_router(settings_router.router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "therepublicbulletin-backend",
        "version": "2.5.0",
    }
