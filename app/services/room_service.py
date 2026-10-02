from collections import OrderedDict
from datetime import date
from decimal import Decimal
from app.models.room import Room
from app.models.booking import Booking


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
    """Duck-typed object for rooms.html / room_detail.html templates."""
    def __init__(self, name, rooms):
        self.name = name
        self.slug = name.lower().replace(" ", "-")
        self.rooms = rooms
        self.capacity = 2
        self.description = rooms[0].description if rooms else ""
        self.amenities = (rooms[0].amenities or "").split(",") if rooms else []
        prices = [r.price for r in rooms if r.price is not None]
        self.base_price = min(prices) if prices else Decimal("0")
        self.rates = _rates(self.base_price)
        imgs = []
        for r in rooms:
            src = r.display_image
            if src:
                if not src.startswith("http") and not src.startswith("/"):
                    src = "/static/" + src
                imgs.append(type("I", (), {"url": src, "alt": name})())
        self.images = imgs
        self.primary_image = imgs[0].url if imgs else ""
        self.available_count = sum(
            1 for r in rooms if (r.status or "available").lower() in ("available", "clean", "")
        )


def get_public_rooms():
    rooms = (
        Room.query.filter_by(is_active=True)
        .order_by(Room.room_type, Room.number)
        .all()
    )
    # filter show_on_website when column present
    filtered = []
    for r in rooms:
        show = getattr(r, "show_on_website", True)
        if show is False:
            continue
        filtered.append(r)
    groups = OrderedDict()
    for r in filtered:
        key = r.room_type or "Standard"
        groups.setdefault(key, []).append(r)
    return [_TypeView(k, v) for k, v in groups.items()]


def get_room_type_detail(type_name: str):
    rooms = Room.query.filter_by(is_active=True, room_type=type_name).order_by(Room.number).all()
    if not rooms:
        return None
    return _TypeView(type_name, rooms)


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
        if b.check_out and b.check_out < today:
            continue
        active.append(b)
    return active


# Backwards-compatible names used by main.py / older routes
def get_enabled_room_types():
    try:
        return get_public_rooms()
    except Exception:
        return []


def get_room_type_by_slug(slug: str):
    if not slug:
        return None
    try:
        rooms = Room.query.filter_by(is_active=True).all()
        types = {r.room_type for r in rooms if r.room_type}
        match = next(
            (
                t
                for t in types
                if t.lower().replace(" ", "-") == slug.lower()
                or t.lower() == slug.lower()
            ),
            None,
        )
        if not match:
            match = slug.replace("-", " ").title()
        return get_room_type_detail(match)
    except Exception:
        return None


def compute_pricing(room_type_id, check_in, check_out):
    """Delegate to room_pricing; also accept type name string as id fallback."""
    from app.services.room_pricing import calculate_stay
    from app.models.room import RoomType, Room
    from decimal import Decimal

    rt = None
    try:
        if room_type_id is not None:
            rt = RoomType.query.get(int(room_type_id))
    except (TypeError, ValueError):
        rt = None

    base = Decimal("0")
    if rt and rt.base_price is not None:
        base = Decimal(str(rt.base_price))
    else:
        # HMS mode: room_type_id may be unused; price from rooms of matching type name
        name = str(room_type_id) if not isinstance(room_type_id, int) else None
        q = Room.query.filter_by(is_active=True)
        if name:
            q = q.filter_by(room_type=name)
        sample = q.first()
        if sample and sample.price is not None:
            base = Decimal(str(sample.price))
        elif rt is None and isinstance(room_type_id, int):
            # try rooms by nothing — average
            sample = Room.query.filter_by(is_active=True).first()
            if sample and sample.price is not None:
                base = Decimal(str(sample.price))

    return calculate_stay(base, check_in, check_out)


def get_available_rooms_for_type(room_type_id, check_in, check_out):
    """
    Rooms of a type not overlapping confirmed bookings in [check_in, check_out).
    Supports RoomType.id (public) or falls back to all active HMS rooms.
    """
    from app.models.room import Room, RoomType
    from app.models.booking import Booking
    from sqlalchemy import and_, or_

    rooms = []
    rt = None
    try:
        rt = RoomType.query.get(int(room_type_id)) if room_type_id is not None else None
    except (TypeError, ValueError):
        rt = None

    if rt:
        # If HMS rooms use string room_type matching RoomType.name
        rooms = (
            Room.query.filter(
                Room.is_active == True,
                or_(
                    Room.room_type == rt.name,
                    # legacy column if present would be room_type_id — ignore if missing
                ),
            )
            .order_by(Room.number)
            .all()
        )
    else:
        rooms = Room.query.filter_by(is_active=True).order_by(Room.number).all()

    # Filter by status
    rooms = [
        r
        for r in rooms
        if (r.status or "available").lower() in ("available", "clean", "")
    ]

    if not check_in or not check_out:
        return rooms

    busy_ids = set()
    try:
        overlaps = Booking.query.filter(
            Booking.status.in_(["pending", "confirmed", "checked_in", "booked"]),
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        ).all()
        for b in overlaps:
            if b.room_id:
                busy_ids.add(b.room_id)
    except Exception:
        pass

    return [r for r in rooms if r.id not in busy_ids]
