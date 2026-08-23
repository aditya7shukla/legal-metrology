import os
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException
from PIL import Image

from app.config import settings


def validate_image_upload(file: UploadFile) -> str:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(settings.ALLOWED_IMAGE_EXTENSIONS)}",
        )
    return ext


def save_upload(file: UploadFile) -> tuple[str, str]:
    """Saves the uploaded image to disk and returns (full_path, thumbnail_path)."""
    ext = validate_image_upload(file)
    filename = f"{uuid.uuid4()}{ext}"
    full_path = os.path.join(settings.UPLOAD_DIR, filename)

    size = 0
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    with open(full_path, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                os.remove(full_path)
                raise HTTPException(
                    status_code=413, detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB."
                )
            out.write(chunk)

    thumb_path = os.path.join(settings.UPLOAD_DIR, f"thumb_{filename}")
    try:
        with Image.open(full_path) as im:
            im.thumbnail((320, 320))
            im.convert("RGB").save(thumb_path, "JPEG", quality=80)
    except Exception:
        thumb_path = None  # non-fatal; thumbnail is a UX nicety only

    return full_path, thumb_path
