"""Auto-seed rooms, tables, menu, reviews when empty. Images editable from public admin."""
from decimal import Decimal
from app import db


def seed_if_empty():
    try:
        _seed_settings()
        _seed_payment_defaults()
        _seed_rooms_and_classes()
        _seed_tables()
        _seed_menu()
        _seed_reviews()
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _seed_settings():
    from app.models.content import HotelSetting
    defaults = [
        ("hotel_name", "Hotel Grand Garden"),
        ("tagline", "Family Restaurant & Lodge"),
        ("address", "Urlabari-05, Morang, Nepal"),
        ("phone", "9816374804"),
        ("email", "hotelgrandnp@outlook.com"),
        ("check_in", "12:00 PM"),
        ("check_out", "11:00 AM"),
        ("latitude", "26.6643"),
        ("longitude", "87.6335"),
    ]
    for k, v in defaults:
        if not HotelSetting.query.filter_by(key=k).first():
            db.session.add(HotelSetting(key=k, value=v))


def _seed_payment_defaults():
    """Advance = fixed Rs amount (not %)."""
    from app.models.admin import PaymentSetting
    defaults = {
        "advance_required": "1",
        "advance_amount_fixed": "1000",  # Rs. 1000 fixed advance
        "advance_percent": "",  # empty = do not use %
        "payment_instructions": "Please pay the advance amount via QR / eSewa / bank and upload the screenshot.",
    }
    for k, v in defaults.items():
        if not PaymentSetting.query.filter_by(key=k).first():
            db.session.add(PaymentSetting(key=k, value=v))


def _seed_rooms_and_classes():
    """Exact Hotel Grand room map."""
    from decimal import Decimal
    from app.models.room import Room, RoomType, RoomImage

    rooms_data = [
        ("Presidential Suite", "presidential-suite", 3000, 4,
         "Spacious presidential suite with premium furnishings.", ["101"]),
        ("Standard Triple Non-AC", "standard-triple-non-ac", 1800, 3,
         "Comfortable triple room without AC.", ["102", "103"]),
        ("Family Non-AC", "family-non-ac", 1800, 4,
         "Family-friendly non-AC room.", ["104", "105", "106", "107"]),
        ("Deluxe Family AC", "deluxe-family-ac", 2500, 4,
         "Air-conditioned deluxe family room.", ["108", "109", "110", "201"]),
        ("Executive AC / Master Suite", "executive-ac-master-suite", 2000, 3,
         "Executive AC room / Master suite.", ["202", "203", "204", "205"]),
    ]
    demo_imgs = [
        "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80",
        "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&q=80",
        "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80",
        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80",
        "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800&q=80",
    ]

    for i, (name, slug, price, cap, desc, numbers) in enumerate(rooms_data):
        rt = RoomType.query.filter(
            (RoomType.slug == slug) | (RoomType.name == name)
        ).first()
        if not rt:
            rt = RoomType(
                name=name,
                slug=slug,
                base_price=Decimal(str(price)),
                capacity=cap,
                description=desc,
                amenities="Free WiFi,TV,Attached Bathroom,Room Service",
                is_enabled=True,
                sort_order=i,
            )
            db.session.add(rt)
            db.session.flush()
            db.session.add(RoomImage(
                room_type_id=rt.id,
                url=demo_imgs[i % len(demo_imgs)],
                image_url=demo_imgs[i % len(demo_imgs)],
                alt=name,
                alt_text=name,
                is_primary=True,
                sort_order=0,
            ))
        else:
            rt.name = name
            rt.slug = slug
            rt.base_price = Decimal(str(price))
            rt.capacity = cap
            rt.is_enabled = True
            rt.sort_order = i
            db.session.flush()

        for num in numbers:
            existing = Room.query.filter_by(number=str(num)).first()
            if not existing:
                db.session.add(Room(
                    number=str(num),
                    room_type=rt.name,
                    price=Decimal(str(price)),
                    description=desc,
                    amenities="Free WiFi,TV,Attached Bathroom",
                    image_url=demo_imgs[i % len(demo_imgs)],
                    status="available",
                    is_active=True,
                    show_on_website=True,
                ))
            else:
                existing.room_type = rt.name
                existing.is_active = True
                existing.price = Decimal(str(price))
                if (existing.status or "").lower() in ("", "disabled", "maintenance"):
                    existing.status = "available"


def _seed_tables():
    from app.models.hms_shared import RestaurantTable
    for n in range(1, 11):
        num = str(n)
        if not RestaurantTable.query.filter_by(number=num).first():
            db.session.add(RestaurantTable(
                number=num,
                seating_capacity=4,
                status="available",
                is_active=True,
            ))


def _seed_menu():
    from app.models.menu import MenuCategory, MenuItem
    if MenuCategory.query.first():
        return
    data = [
        ("Food", [
            ("Chicken Momo", 180, "Steamed chicken dumplings"),
            ("Veg Chowmein", 150, "Stir-fried noodles"),
            ("Thukpa", 160, "Himalayan noodle soup"),
            ("Fried Rice", 170, "Egg fried rice"),
            ("Chicken Chili", 280, "Spicy chicken"),
        ]),
        ("Drinks", [
            ("Milk Tea", 40, "Local milk tea"),
            ("Black Tea", 30, "Plain tea"),
            ("Cold Drinks", 60, "Soft drinks"),
            ("Fresh Juice", 120, "Seasonal juice"),
        ]),
        ("Bar", [
            ("Local Beer", 350, "500ml"),
            ("Whisky Shot", 200, "30ml"),
        ]),
    ]
    food_img = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80"
    drink_img = "https://images.unsplash.com/photo-1544145945-f9042533c2c0?w=600&q=80"
    for ci, (cname, items) in enumerate(data):
        cat = MenuCategory(name=cname, sort_order=ci, is_active=True)
        db.session.add(cat)
        db.session.flush()
        for ii, (name, price, desc) in enumerate(items):
            img = food_img if cname == "Food" else drink_img
            db.session.add(MenuItem(
                category_id=cat.id,
                name=name,
                description=desc,
                price=Decimal(str(price)),
                image_url=img,
                is_available=True,
                is_active=True,
                show_on_website=True,
                show_on_qr=True,
                sort_order=ii,
            ))


def _seed_reviews():
    from app.models.content import Review
    if Review.query.first():
        return
    samples = [
        ("Sita R.", 5, "Clean rooms and very friendly staff. Great food at the restaurant."),
        ("Ramesh K.", 5, "Best stay in Urlabari. Location is convenient and service is excellent."),
        ("Anita M.", 4, "Comfortable family room. Breakfast was delicious."),
        ("John D.", 5, "Warm hospitality. Highly recommend Hotel Grand Garden."),
    ]
    for name, rating, content in samples:
        db.session.add(Review(
            author_name=name,
            rating=rating,
            content=content,
            is_published=True,
        ))
