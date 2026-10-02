from collections import OrderedDict
from datetime import date
from decimal import Decimal
from hotel_site.models.room import Room, RoomType
from hotel_site.models.booking import Booking


def _fmt(amount):
    try:
        return f"Rs. {float(amount):,.0f}"
    except Exception:
        return "Rs. 0"


def _rates(base):
    base = Decimal(str(base or 0))
    weekend = max(Decimal("0"), base - Decimal("200"))
    return {
        "normal": base,
        "weekend": weekend,
        "normal_formatted": _fmt(base),
        "weekend_formatted": _fmt(weekend),
    }


class _TypeView:
    def __init__(self, name, rooms=None, rt=None):
        self.name = name
        self.slug = (rt.slug if rt and rt.slug else name.lower().replace(" ", "-"))
        self.rooms = rooms or []
        self.capacity = (rt.capacity if rt else 2) or 2
        self.description = (rt.description if rt else None) or (rooms[0].description if rooms else "")
        amenities = (rt.amenities if rt else None) or (rooms[0].amenities if rooms else "")
        self.amenities = [a.strip() for a in (amenities or "").split(",") if a.strip()]
        base = (rt.base_price if rt else None)
        if base is None and rooms:
            prices = [r.price for r in rooms if r.price is not None]
            base = min(prices) if prices else Decimal("0")
        self.base_price = base or Decimal("0")
        self.rates = _rates(self.base_price)
        imgs = []
        if rt is not None:
            try:
                from hotel_site.models.room import RoomImage
                q = RoomImage.query.filter_by(room_type_id=rt.id).order_by(RoomImage.sort_order)
                for im in q.all():
                    src = im.display_url or im.image_url or im.url
                    if src:
                        imgs.append(type("I", (), {"url": src, "alt": name})())
            except Exception:
                pass
        if not imgs and rooms:
            for r in rooms:
                src = r.display_image
                if src:
                    if not str(src).startswith("http") and not str(src).startswith("/"):
                        src = "/static/" + src
                    imgs.append(type("I", (), {"url": src, "alt": name})())
        self.images = imgs
        self.primary_image = imgs[0].url if imgs else ""
        self.available_count = sum(
            1 for r in self.rooms if (getattr(r, "status", None) or "available").lower() in ("available", "clean", "")
        ) if self.rooms else 1



def get_public_rooms():
    # Prefer RoomType cards (seeded / public admin images)
    types = RoomType.query.filter_by(is_enabled=True).order_by(RoomType.sort_order, RoomType.name).all()
    if types:
        out = []
        for rt in types:
            rooms = Room.query.filter_by(is_active=True, room_type=rt.name).order_by(Room.number).all()
            out.append(_TypeView(rt.name, rooms=rooms, rt=rt))
        return out

    # Fallback: group HMS rooms by room_type string
    rooms = Room.query.filter_by(is_active=True).order_by(Room.room_type, Room.number).all()
    groups = OrderedDict()
    for r in rooms:
        if getattr(r, "show_on_website", True) is False:
            continue
        key = r.room_type or "Standard"
        groups.setdefault(key, []).append(r)
    return [_TypeView(k, v) for k, v in groups.items()]


def get_room_type_detail(type_name: str):
    rt = RoomType.query.filter(
        (RoomType.name == type_name) | (RoomType.slug == type_name.lower().replace(" ", "-"))
    ).first()
    rooms = Room.query.filter_by(is_active=True, room_type=type_name).order_by(Room.number).all()
    if rt:
        return _TypeView(rt.name, rooms=rooms, rt=rt)
    if rooms:
        return _TypeView(type_name, rooms=rooms)
    return None


def get_occupied_bookings():
    today = date.today()
    try:
        rows = (
            Booking.query.filter(
                Booking.status.in_(["confirmed", "checked_in", "booked", "occupied"])
            )
            .order_by(Booking.check_in.desc())
            .limit(100)
            .all()
        )
    except Exception:
        return []
    active = []
    for b in rows:
        co = b.check_out
        if co and hasattr(co, "date"):
            co = co.date()
        if co and co < today:
            continue
        active.append(b)
    return active


def get_enabled_room_types():
    try:
        return get_public_rooms()
    except Exception:
        return []


def get_room_type_by_slug(slug: str):
    if not slug:
        return None
    rt = RoomType.query.filter_by(slug=slug).first()
    if rt:
        return get_room_type_detail(rt.name)
    return get_room_type_detail(slug.replace("-", " ").title())


def compute_pricing(room_type_id, check_in, check_out):
    from hotel_site.services.room_pricing import calculate_stay
    from decimal import Decimal

    rt = None
    try:
        if room_type_id is not None:
            rt = RoomType.query.get(int(room_type_id))
    except (TypeError, ValueError):
        rt = None
    base = Decimal(str(rt.base_price)) if rt and rt.base_price is not None else Decimal("0")
    if base == 0:
        sample = Room.query.filter_by(is_active=True).first()
        if sample and sample.price is not None:
            base = Decimal(str(sample.price))
    return calculate_stay(base, check_in, check_out)



def get_available_rooms_for_type(room_type_id, check_in, check_out):
    """Rooms for a RoomType that are free between check_in and check_out."""
    from datetime import datetime, date, time
    from hotel_site.models.room import Room, RoomType
    from hotel_site.models.booking import Booking

    rt = None
    try:
        rt = RoomType.query.get(int(room_type_id)) if room_type_id is not None else None
    except (TypeError, ValueError):
        rt = None

    if rt:
        rooms = (
            Room.query.filter(Room.is_active == True)
            .filter(
                (Room.room_type == rt.name)
                | (Room.room_type == rt.slug)
                | (Room.room_type.ilike(rt.name))
            )
            .order_by(Room.number)
            .all()
        )
        # If none linked by name yet, create is not done here — return empty
    else:
        rooms = Room.query.filter_by(is_active=True).order_by(Room.number).all()

    rooms = [
        r for r in rooms
        if (getattr(r, "status", None) or "available").lower() in ("available", "clean", "")
    ]

    if not check_in or not check_out:
        return rooms

    # Normalize to date
    def as_date(v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return v

    ci, co = as_date(check_in), as_date(check_out)
    busy_ids = set()
    try:
        overlaps = Booking.query.filter(
            Booking.status.in_(["pending", "confirmed", "checked_in", "booked"])
        ).all()
        for b in overlaps:
            b_ci = as_date(b.check_in)
            b_co = as_date(b.check_out)
            if not b_ci or not b_co:
                continue
            # overlap: b_ci < co and b_co > ci
            if b_ci < co and b_co > ci and b.room_id:
                busy_ids.add(b.room_id)
    except Exception:
        try:
            from hotel_site import db
            db.session.rollback()
        except Exception:
            pass

    return [r for r in rooms if r.id not in busy_ids]
