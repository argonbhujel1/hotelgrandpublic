from flask import Blueprint, render_template
from app.services.content_service import get_hotel_info
from app.services.menu_service import get_website_menu
from app.services.room_service import get_occupied_bookings

restaurant_bp = Blueprint("restaurant", __name__)


@restaurant_bp.route("/")
def menu():
    hotel = get_hotel_info()
    categories = get_website_menu()
    occupied = []
    try:
        occupied = get_occupied_bookings()
    except Exception:
        occupied = []
    return render_template(
        "restaurant.html",
        hotel=hotel,
        categories=categories,
        occupied_bookings=occupied,
    )
