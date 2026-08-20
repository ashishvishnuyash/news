from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.auth import require_role


router = APIRouter(prefix="/api/media", tags=["Media"])

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_BYTES = 8 * 1024 * 1024


def image_extension(data: bytes) -> str | None:
    """Return an extension only for image formats we safely serve."""
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return None


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    _current_user= require_role(["JOURNALIST", "EDITOR", "ADMIN"]),
):
    """Store a journalist's JPEG, PNG, or WebP cover image and return its public URL."""
    try:
        contents = await file.read(MAX_IMAGE_BYTES + 1)
    finally:
        await file.close()

    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose an image file to upload.")
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image files must be 8 MB or smaller.",
        )

    extension = image_extension(contents)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Use a JPEG, PNG, or WebP image.",
        )

    filename = f"{uuid4().hex}{extension}"
    destination = UPLOADS_DIR / filename
    destination.write_bytes(contents)
    return {"url": str(request.url_for("media", path=filename))}
