from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from app.services.content_service import (
    get_hotel_info, get_hero, get_about, get_policies,
    get_published_reviews, get_amenities, get_seminar_hall, get_outdoor_event, get_parking_info, get_gallery_images
)
from app.services.room_service import get_enabled_room_types

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    hotel = get_hotel_info()
    hero = get_hero()
    rooms = get_enabled_room_types()[:4]
    reviews = get_published_reviews(6)
    amenities = get_amenities()
    about = get_about()
    seminar = get_seminar_hall()
    outdoor = get_outdoor_event()
    parking = get_parking_info()
    return render_template(
        "home.html",
        hotel=hotel,
        hero=hero,
        rooms=rooms,
        reviews=reviews,
        amenities=amenities,
        about=about,
        seminar=seminar,
        outdoor=outdoor,
        parking=parking,
        gallery_images=get_gallery_images(),
    )


@main_bp.route("/amenities")
def amenities_page():
    hotel = get_hotel_info()
    amenities = get_amenities()
    return render_template("amenities.html", hotel=hotel, amenities=amenities)


@main_bp.route("/events")
def events():
    hotel = get_hotel_info()
    seminar = get_seminar_hall()
    outdoor = get_outdoor_event()
    parking = get_parking_info()
    return render_template(
        "events.html",
        hotel=hotel,
        seminar=seminar,
        outdoor=outdoor,
        parking=parking,
        gallery_images=get_gallery_images(),
    )


@main_bp.route("/about")
def about():
    hotel = get_hotel_info()
    about_data = get_about()
    return render_template(
        "about.html",
        hotel=hotel,
        about=about_data,
        gallery_images=get_gallery_images(),
    )


@main_bp.route("/review", methods=["POST"])
def submit_review():
    """Public review submission — pending admin publish."""
    from app import db
    from app.models.content import Review
    name = (request.form.get("author_name") or "").strip()[:100]
    content = (request.form.get("content") or "").strip()[:2000]
    try:
        rating = int(request.form.get("rating", 5) or 5)
    except ValueError:
        rating = 5
    rating = max(1, min(5, rating))
    if not name or not content:
        flash("Please enter your name and review.", "error")
        return redirect(url_for("main.home") + "#reviews")
    db.session.add(Review(
        author_name=name,
        content=content,
        rating=rating,
        is_published=False,
    ))
    db.session.commit()
    flash("Thank you! Your review was submitted and will appear after approval.", "success")
    return redirect(url_for("main.home") + "#reviews")


@main_bp.route("/location")
def location():
    hotel = get_hotel_info()
    return render_template("location.html", hotel=hotel)


@main_bp.route("/robots.txt")
def robots():
    return current_app.send_static_file("robots.txt")


@main_bp.route("/sitemap.xml")
def sitemap():
    return current_app.send_static_file("sitemap.xml")
