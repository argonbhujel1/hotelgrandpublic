from flask import Blueprint, render_template, abort
from hotel_site.services.content_service import get_hotel_info
from hotel_site.services.room_service import get_public_rooms, get_room_type_detail
from hotel_site.models.room import Room

rooms_bp = Blueprint("rooms", __name__)


@rooms_bp.route("/")
def list_rooms():
    hotel = get_hotel_info()
    rooms = get_public_rooms()  # template loops `{% for room in rooms %}`
    return render_template("rooms.html", hotel=hotel, rooms=rooms)


@rooms_bp.route("/<path:slug>")
def room_detail(slug):
    hotel = get_hotel_info()
    types = {r.room_type for r in Room.query.filter_by(is_active=True).all()}
    match = next(
        (t for t in types if t.lower().replace(" ", "-") == slug.lower() or t.lower() == slug.lower()),
        None,
    )
    if not match:
        # try title case of slug
        match = slug.replace("-", " ").title()
        detail = get_room_type_detail(match)
        if not detail:
            abort(404)
    else:
        detail = get_room_type_detail(match)
        if not detail:
            abort(404)
    return render_template("room_detail.html", hotel=hotel, room=detail)
