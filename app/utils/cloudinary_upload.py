"""Cloudinary image upload helper.

Env (any one style works):
  CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
  or
  CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET
"""
from __future__ import annotations
import os


def cloudinary_configured() -> bool:
    if os.environ.get("CLOUDINARY_URL"):
        return True
    return bool(
        os.environ.get("CLOUDINARY_CLOUD_NAME")
        and os.environ.get("CLOUDINARY_API_KEY")
        and os.environ.get("CLOUDINARY_API_SECRET")
    )


def upload_image(file_storage, folder: str = "hotel-grand") -> str | None:
    """Upload to Cloudinary; return secure HTTPS URL or None."""
    if not file_storage or not getattr(file_storage, "filename", None):
        return None
    if not cloudinary_configured():
        return None
    try:
        import cloudinary
        import cloudinary.uploader

        if os.environ.get("CLOUDINARY_URL"):
            cloudinary.config(cloudinary_url=os.environ["CLOUDINARY_URL"])
        else:
            cloudinary.config(
                cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
                api_key=os.environ["CLOUDINARY_API_KEY"],
                api_secret=os.environ["CLOUDINARY_API_SECRET"],
                secure=True,
            )
        result = cloudinary.uploader.upload(
            file_storage,
            folder=f"hotel-grand/{folder}",
            resource_type="image",
            overwrite=False,
            unique_filename=True,
            transformation=[
                {"quality": "auto", "fetch_format": "auto"},
            ],
        )
        return result.get("secure_url") or result.get("url")
    except Exception as e:
        try:
            from flask import current_app
            current_app.logger.warning("Cloudinary upload failed: %s", e)
        except Exception:
            pass
        return None
