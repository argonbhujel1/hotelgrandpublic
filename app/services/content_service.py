"""Content helpers for public website pages."""
from flask import current_app


def _setting(key, default=""):
    try:
        from app.models.content import HotelSetting
        row = HotelSetting.query.filter_by(key=key).first()
        if row and row.value is not None:
            return row.value
    except Exception:
        pass
    return default


def _page(key):
    try:
        from app.models.content import PageContent
        return PageContent.query.filter_by(page_key=key).first()
    except Exception:
        return None


def get_hotel_info():
    name = _setting("hotel_name") or current_app.config.get("HOTEL_NAME", "Hotel Grand")
    return {
        "name": name,
        "tagline": _setting("tagline") or current_app.config.get("HOTEL_TAGLINE", ""),
        "phone": _setting("phone") or current_app.config.get("HOTEL_PHONE", ""),
        "email": _setting("email") or current_app.config.get("HOTEL_EMAIL", ""),
        "address": _setting("address") or current_app.config.get("HOTEL_ADDRESS", ""),
        "map_embed": _setting("map_embed", ""),
        "facebook": _setting("facebook", ""),
        "instagram": _setting("instagram", ""),
        "whatsapp": _setting("whatsapp", ""),
    }


def get_hero():
    p = _page("hero")
    if p:
        return {
            "title": p.title or "Welcome",
            "subtitle": p.subtitle or "",
            "body": p.body or "",
            "image_url": p.image_url or "",
        }
    return {
        "title": _setting("hero_title", "Hotel Grand Garden"),
        "subtitle": _setting("hero_subtitle", "Comfort in the heart of nature"),
        "body": _setting("hero_body", ""),
        "image_url": _setting("hero_image", ""),
    }


def get_about():
    p = _page("about")
    if p:
        return {
            "title": p.title or "About Us",
            "subtitle": p.subtitle or "",
            "body": p.body or "",
            "image_url": p.image_url or "",
        }
    return {
        "title": "About Us",
        "subtitle": "",
        "body": _setting("about_body", ""),
        "image_url": _setting("about_image", ""),
    }


def get_policies():
    p = _page("policies")
    if p:
        return {"title": p.title or "Policies", "body": p.body or ""}
    return {"title": "Policies", "body": _setting("policies", "")}


def get_payment_info():
    try:
        from app.models.admin import PaymentSetting
        rows = PaymentSetting.query.all()
        return {r.key: r.value for r in rows}
    except Exception:
        return {}


def get_published_reviews(limit=6):
    try:
        from app.models.content import Review
        return (
            Review.query.filter_by(is_published=True)
            .order_by(Review.sort_order, Review.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception:
        return []


def get_amenities():
    try:
        from app.models.content import Amenity
        return (
            Amenity.query.filter_by(is_enabled=True)
            .order_by(Amenity.sort_order, Amenity.name)
            .all()
        )
    except Exception:
        return []


def get_seminar_hall():
    try:
        from app.models.content import SeminarHall
        return SeminarHall.query.filter_by(is_enabled=True).first()
    except Exception:
        return None


def get_outdoor_event():
    try:
        from app.models.content import OutdoorEvent
        return OutdoorEvent.query.filter_by(is_enabled=True).first()
    except Exception:
        return None


def get_parking_info():
    return {
        "title": _setting("parking_title", "Parking"),
        "body": _setting("parking_body", ""),
        "image_url": _setting("parking_image", ""),
    }


def get_gallery_images():
    """Return list of image URL strings for gallery sections."""
    images = []
    try:
        from app.models.room import RoomImage
        for img in RoomImage.query.order_by(RoomImage.sort_order).limit(24).all():
            u = img.display_url
            if u:
                images.append(u)
    except Exception:
        pass
    extra = _setting("gallery_urls", "")
    if extra:
        for part in extra.replace("\n", ",").split(","):
            p = part.strip()
            if p:
                images.append(p)
    return images
