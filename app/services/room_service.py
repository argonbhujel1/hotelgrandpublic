"""Room helpers for public website."""
from datetime import date


class _RoomTypeView:
    """Shape expected by rooms.html / home templates."""

    def __init__(self, rt, primary_image="", sample_price=0):
        self.id = rt.id
        self.name = rt.name
        self.slug = rt.slug or (rt.name or "").lower().replace(" ", "-")
        self.description = rt.description or ""
        self.capacity = rt.capacity or 2
        self.amenities = rt.amenities or ""
        self.base_price = rt.base_price or sample_price or 0
        self.primary_image = primary_image
        self.image_url = primary_image
        try:
            bp = float(self.base_price or 0)
        except Exception:
            bp = 0
        weekend = bp * 0.9 if bp else 0
        self.rates = {
            "normal": bp,
            "weekend": weekend,
            "normal_formatted": f"Rs. {bp:,.0f}",
            "weekend_formatted": f"Rs. {weekend:,.0f}",
        }


def get_enabled_room_types():
    """List of RoomType views for homepage / booking."""
    try:
        from app.models.room import RoomType, RoomImage, Room
        types = (
            RoomType.query.filter_by(is_enabled=True)
            .order_by(RoomType.sort_order, RoomType.name)
            .all()
        )
        result = []
        for rt in types:
            images = list(rt.images.order_by(RoomImage.sort_order).all()) if hasattr(rt, "images") else []
            primary = next((i.display_url for i in images if i.is_primary), None)
            if not primary and images:
                primary = images[0].display_url
            if not primary:
                # try physical room image
                pr = Room.query.filter(
                    (Room.room_type == rt.name) | (Room.room_type == rt.slug),
                    Room.is_active == True,  # noqa: E712
                ).first()
                if pr:
                    primary = pr.display_image
            price = rt.base_price
            if not price:
                pr = Room.query.filter(
                    (Room.room_type == rt.name) | (Room.room_type == rt.slug)
                ).first()
                if pr:
                    price = pr.price
            result.append(_RoomTypeView(rt, primary or "", price or 0))
        return result
    except Exception:
        return []


def get_public_rooms():
    """For rooms list page — same as enabled room types (card grid)."""
    return get_enabled_room_types()


def get_room_type_by_slug(slug):
    if not slug:
        return None
    try:
        from app.models.room import RoomType
        slug = slug.lower().strip()
        rt = RoomType.query.filter_by(slug=slug, is_enabled=True).first()
        if rt:
            return rt
        for r in RoomType.query.filter_by(is_enabled=True).all():
            if (r.slug or "").lower() == slug or (r.name or "").lower().replace(" ", "-") == slug:
                return r
            if (r.name or "").lower() == slug:
                return r
    except Exception:
        pass
    return None


def get_room_type_detail(type_name):
    """Detail object for room_detail template."""
    if not type_name:
        return None
    try:
        from app.models.room import RoomType, Room, RoomImage
        rt = RoomType.query.filter(
            (RoomType.name == type_name) | (RoomType.slug == type_name)
        ).first()
        if not rt:
            for r in RoomType.query.all():
                if (r.name or "").lower() == type_name.lower():
                    rt = r
                    break
        if not rt:
            rooms = Room.query.filter(
                Room.room_type == type_name, Room.is_active == True  # noqa: E712
            ).all()
            if not rooms:
                return None
            sample = rooms[0]
            try:
                bp = float(sample.price or 0)
            except Exception:
                bp = 0
            return {
                "name": type_name,
                "slug": type_name.lower().replace(" ", "-"),
                "description": sample.description or "",
                "base_price": sample.price or 0,
                "capacity": 2,
                "amenities": sample.amenities or "",
                "image_url": sample.display_image,
                "primary_image": sample.display_image,
                "rooms": rooms,
                "images": [],
                "rates": {
                    "normal_formatted": f"Rs. {bp:,.0f}",
                    "weekend_formatted": f"Rs. {bp * 0.9:,.0f}",
                },
            }
        images = list(rt.images.order_by(RoomImage.sort_order).all()) if hasattr(rt, "images") else []
        primary = next((i.display_url for i in images if i.is_primary), None)
        if not primary and images:
            primary = images[0].display_url
        physical = Room.query.filter(
            (Room.room_type == rt.name) | (Room.room_type == rt.slug),
            Room.is_active == True,  # noqa: E712
        ).order_by(Room.number).all()
        try:
            bp = float(rt.base_price or 0)
        except Exception:
            bp = 0
        return {
            "name": rt.name,
            "slug": rt.slug or rt.name.lower().replace(" ", "-"),
            "description": rt.description or "",
            "base_price": rt.base_price or 0,
            "capacity": rt.capacity or 2,
            "amenities": rt.amenities or "",
            "image_url": primary or "",
            "primary_image": primary or "",
            "rooms": physical,
            "images": images,
            "id": rt.id,
            "rates": {
                "normal_formatted": f"Rs. {bp:,.0f}",
                "weekend_formatted": f"Rs. {bp * 0.9:,.0f}",
            },
        }
    except Exception:
        return None


def get_available_rooms_for_type(type_name, check_in=None, check_out=None):
    try:
        from app.models.room import Room
        rooms = Room.query.filter(
            Room.room_type == type_name,
            Room.is_active == True,  # noqa: E712
            Room.status.in_(["available", "Available", "AVAILABLE"]),
        ).order_by(Room.number).all()
        if not rooms:
            rooms = Room.query.filter(
                Room.room_type == type_name,
                Room.is_active == True,  # noqa: E712
            ).order_by(Room.number).all()
        return rooms
    except Exception:
        return []


def get_occupied_bookings():
    try:
        from app.models.booking import Booking
        today = date.today()
        return (
            Booking.query.filter(
                Booking.status.in_(["confirmed", "checked_in", "pending"]),
                Booking.check_in <= today,
                Booking.check_out >= today,
            )
            .order_by(Booking.check_in)
            .limit(50)
            .all()
        )
    except Exception:
        return []
