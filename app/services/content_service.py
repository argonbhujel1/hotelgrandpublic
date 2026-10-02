from flask import current_app
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.models.content import (
    HotelSetting, Review, Amenity, SeminarHall, OutdoorEvent, PageContent
)


def _safe_query(fn, default=None):
    """Run a DB query; return default if tables are missing."""
    try:
        return fn()
    except (OperationalError, ProgrammingError):
        return default


def get_setting(key: str, default=None):
    def _q():
        s = HotelSetting.query.filter_by(key=key).first()
        return s.value if s else default
    return _safe_query(_q, default)


def get_hotel_info():
    return {
        "name": get_setting("hotel_name") or current_app.config["HOTEL_NAME"],
        "tagline": get_setting("tagline") or current_app.config["HOTEL_TAGLINE"],
        "address": get_setting("address") or current_app.config["HOTEL_ADDRESS"],
        "phone": get_setting("phone") or current_app.config["HOTEL_PHONE"],
        "email": get_setting("email") or current_app.config["HOTEL_EMAIL"],
        "check_in": get_setting("check_in") or current_app.config["CHECK_IN"],
        "check_out": get_setting("check_out") or current_app.config["CHECK_OUT"],
        "lat": float(get_setting("latitude") or current_app.config["HOTEL_LAT"]),
        "lng": float(get_setting("longitude") or current_app.config["HOTEL_LNG"]),
        "logo_url": get_setting("logo_url") or "",
    }


def get_hero():
    page = _safe_query(lambda: PageContent.query.filter_by(page_key="hero").first())
    if page:
        return {
            "title": page.title or "Hotel Grand",
            "subtitle": page.subtitle or "Luxury Family Stay",
            "body": page.body or "Restaurant & Bar · Seminar Hall · Outdoor Events",
            "image_url": page.image_url,
        }
    return {
        "title": "Hotel Grand",
        "subtitle": "Luxury Family Stay",
        "body": "Restaurant & Bar · Seminar Hall · Outdoor Events",
        "image_url": None,
    }


def get_about():
    page = _safe_query(lambda: PageContent.query.filter_by(page_key="about").first())
    if page:
        return {
            "title": page.title or "About Hotel Grand",
            "body": page.body or "",
            "image_url": page.image_url,
        }
    return {
        "title": "About Hotel Grand",
        "body": (
            "Hotel Grand is a premier destination in Urlabari-05, Morang, Nepal, "
            "offering comfortable family stays, a vibrant restaurant & bar, "
            "a spacious seminar hall, and beautiful outdoor event spaces. "
            "Whether you are travelling for leisure, hosting a celebration, or conducting business, "
            "we welcome you with warm hospitality and modern amenities."
        ),
        "image_url": None,
    }


def get_policies():
    page = _safe_query(lambda: PageContent.query.filter_by(page_key="policies").first())
    if page and page.body:
        return page.body
    return (
        "Check-in: 12:00 PM · Check-out: 11:00 AM\n"
        "• Advance payment is mandatory to confirm your booking.\n"
        "• Free cancellation up to 24 hours before check-in.\n"
        "• Valid government-issued ID is required at check-in."
    )


def get_published_reviews(limit=12):
    return _safe_query(
        lambda: (
            Review.query
            .filter_by(is_published=True)
            .order_by(Review.sort_order, Review.created_at.desc())
            .limit(limit)
            .all()
        ),
        [],
    ) or []


def get_amenities():
    return _safe_query(
        lambda: (
            Amenity.query
            .filter_by(is_enabled=True)
            .order_by(Amenity.sort_order, Amenity.name)
            .all()
        ),
        [],
    ) or []


def get_seminar_hall():
    return _safe_query(lambda: SeminarHall.query.filter_by(is_enabled=True).first())


def get_outdoor_event():
    return _safe_query(lambda: OutdoorEvent.query.filter_by(is_enabled=True).first())


def get_payment_info():
    """Public payment/QR settings for booking page."""
    from app.models.admin import PaymentSetting
    def g(k, d=""):
        try:
            s = PaymentSetting.query.filter_by(key=k).first()
            return s.value if s else d
        except Exception:
            return d
    return {
        "advance_required": g("advance_required", "1") == "1",
        "advance_percent": g("advance_percent", ""),
        "advance_amount_fixed": g("advance_amount_fixed", "1000"),
        "payment_instructions": g("payment_instructions", ""),
        "esewa_id": g("esewa_id", ""),
        "khalti_id": g("khalti_id", ""),
        "bank_name": g("bank_name", ""),
        "bank_account": g("bank_account", ""),
        "bank_account_name": g("bank_account_name", ""),
        "qr_image": g("qr_image", ""),
    }


def get_parking_info():
    return {
        "info": get_setting("parking_info") or "Free on-site parking for hotel guests and event visitors.",
        "free": (get_setting("parking_free") or "1") == "1",
        "image": get_setting("parking_image") or "",
    }


def get_gallery_images():
    """Combine admin gallery uploads + room, menu, seminar, outdoor, parking photos."""
    import json
    seen = set()
    imgs = []

    def add(url):
        if not url:
            return
        u = str(url).strip()
        if not u or u in seen:
            return
        seen.add(u)
        imgs.append(u)

    # 1) Explicit gallery uploads
    raw = get_setting("gallery_images")
    if raw:
        try:
            for u in json.loads(raw):
                add(u)
        except Exception:
            pass

    # 2) Room type images
    try:
        from app.models.room import RoomType, RoomImage
        for rt in RoomType.query.filter_by(is_enabled=True).all():
            for ri in RoomImage.query.filter_by(room_type_id=rt.id).order_by(RoomImage.sort_order).all():
                add(ri.image_url)
    except Exception:
        pass

    # 3) Menu item images
    try:
        from app.models.menu import MenuItem
        for it in MenuItem.query.filter_by(is_available=True, show_on_website=True).all():
            add(it.image_url)
    except Exception:
        pass

    # 4) Seminar / outdoor
    try:
        from app.models.content import SeminarHall, OutdoorEvent
        s = SeminarHall.query.filter_by(is_enabled=True).first()
        if s:
            add(s.image_url)
        o = OutdoorEvent.query.filter_by(is_enabled=True).first()
        if o:
            add(o.image_url)
    except Exception:
        pass

    # 5) Parking
    add(get_setting("parking_image"))

    # Fallback demos if still empty
    if not imgs:
        imgs = [
            "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=600&q=80",
            "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=600&q=80",
            "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600&q=80",
            "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&q=80",
            "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=600&q=80",
            "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=600&q=80",
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&q=80",
            "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&q=80",
        ]
    return imgs

