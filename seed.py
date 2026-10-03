"""
Demo seed for local development only.
In production, HMS owns this data — do not re-seed production.
"""
from decimal import Decimal
from hotel_site import db
from hotel_site.models.room import RoomType, Room, RoomImage
from hotel_site.models.menu import MenuCategory, MenuItem
from hotel_site.models.content import Review, Amenity, SeminarHall, OutdoorEvent, PageContent, HotelSetting
from hotel_site.models.admin import AdminUser, PaymentSetting


def seed_demo():
    if RoomType.query.first():
        print("Data already exists — skipping seed.")
        return

    # Settings
    settings = [
        ("hotel_name", "Hotel Grand"),
        ("tagline", "Family Restaurant & Lodge"),
        ("address", "Urlabari-05, Morang, Nepal"),
        ("phone", "021-541955"),
        ("email", "info@hotelgrand.com.np"),
        ("check_in", "12:00 PM"),
        ("check_out", "11:00 AM"),
        ("latitude", "26.6643"),
        ("longitude", "87.6335"),
    ]
    for k, v in settings:
        db.session.add(HotelSetting(key=k, value=v))

    # Room types
    rooms_data = [
        ("Presidential Suite", "presidential-suite", 3000, 4, "Spacious presidential suite with premium furnishings, ideal for families seeking luxury."),
        ("Standard Triple", "standard-triple", 1800, 3, "Comfortable triple room with essential amenities for a pleasant stay."),
        ("Family Room", "family-room", 1800, 4, "Family-friendly room with space for everyone."),
        ("Deluxe AC Family", "deluxe-ac-family", 2500, 4, "Air-conditioned deluxe family room with modern comforts."),
        ("Master Suite", "master-suite", 2000, 3, "Elegant master suite for a refined stay."),
    ]
    for i, (name, slug, price, cap, desc) in enumerate(rooms_data):
        rt = RoomType(
            name=name,
            slug=slug,
            base_price=Decimal(str(price)),
            capacity=cap,
            description=desc,
            amenities="Free WiFi,TV,Attached Bathroom,AC,Room Service",
            is_enabled=True,
            sort_order=i,
        )
        db.session.add(rt)
        db.session.flush()
        # Demo class image (replace from admin with real photos)
        demo_imgs = [
            "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80",
            "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&q=80",
            "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80",
            "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80",
            "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800&q=80",
        ]
        db.session.add(RoomImage(
            room_type_id=rt.id,
            image_url=demo_imgs[i % len(demo_imgs)],
            alt_text=name,
            is_primary=True,
            sort_order=0,
        ))
        # Sample rooms
        for n in range(1, 3):
            db.session.add(Room(
                room_type_id=rt.id,
                room_number=f"{100 + i * 10 + n}",
                status="available",
                is_enabled=True,
            ))

    # Menu
    cats = [
        ("Food", "food", [
            ("Chicken Momo", "Steamed chicken dumplings", 250),
            ("Veg Chowmein", "Stir-fried noodles with vegetables", 200),
            ("Chicken Biryani", "Fragrant rice with spiced chicken", 350),
            ("Thukpa", "Tibetan noodle soup", 280),
            ("Dal Bhat Tarkari", "Traditional Nepali set meal", 300),
            ("Grilled Fish", "Fresh grilled fish", 450),
            ("Club Sandwich", "Classic club sandwich", 320),
            ("Chocolate Brownie", "Warm chocolate brownie", 180),
        ]),
        ("Drinks", "drinks", [
            ("Fresh Lime Soda", "Refreshing lime soda", 120),
            ("Local Beer", "Chilled local beer", 350),
        ]),
    ]
    for ci, (cname, cslug, items) in enumerate(cats):
        cat = MenuCategory(name=cname, slug=cslug, sort_order=ci, is_enabled=True)
        db.session.add(cat)
        db.session.flush()
        for ii, (iname, idesc, iprice) in enumerate(items):
            db.session.add(MenuItem(
                category_id=cat.id,
                name=iname,
                description=idesc,
                price=Decimal(str(iprice)),
                is_available=True,
                show_on_website=True,
                show_on_qr=True,
                is_orderable=True,
                sort_order=ii,
            ))

    # Reviews
    for name, content, rating in [
        ("Anil S.", "Excellent hospitality and clean rooms. The restaurant food was delicious. Highly recommended for families.", 5),
        ("Sita K.", "Great location in Urlabari. Staff were friendly and the seminar hall worked perfectly for our meeting.", 5),
        ("Ramesh K.", "Comfortable stay, good parking, and the outdoor space is beautiful for events. Will visit again.", 4),
    ]:
        db.session.add(Review(author_name=name, content=content, rating=rating, is_published=True))

    # Amenities
    for i, name in enumerate([
        "Free WiFi", "Free Parking", "Restaurant", "Bar", "AC Rooms",
        "Room Service", "Seminar Hall", "Outdoor Events", "24/7 Front Desk",
        "Laundry", "TV", "Attached Bathroom",
    ]):
        db.session.add(Amenity(name=name, is_enabled=True, sort_order=i))

    # Seminar & Outdoor
    db.session.add(SeminarHall(
        title="Seminar Hall",
        description="Spacious seminar hall ideal for meetings, workshops and small conferences.",
        capacity=150,
        day_rate=Decimal("15000"),
        hourly_rate=Decimal("2000"),
        is_enabled=True,
    ))
    db.session.add(OutdoorEvent(
        title="Outdoor Events",
        description="Beautiful outdoor grounds suitable for weddings, parties and large celebrations. Free parking available.",
        capacity=500,
        features="weddings,parties,free parking",
        is_enabled=True,
    ))

    # Page content
    db.session.add(PageContent(
        page_key="hero",
        title="Hotel Grand",
        subtitle="Luxury Family Stay",
        body="Restaurant & Bar · Seminar Hall · Outdoor Events",
    ))
    db.session.add(PageContent(
        page_key="about",
        title="About Hotel Grand",
        body=(
            "Hotel Grand is a premier destination in Urlabari-05, Morang, Nepal, "
            "offering comfortable family stays, a vibrant restaurant & bar, "
            "a spacious seminar hall, and beautiful outdoor event spaces."
        ),
    ))


    # Default admin — change password after first login
    if not AdminUser.query.filter_by(username="admin").first():
        admin = AdminUser(username="admin", is_active=True)
        admin.set_password("admin123")
        db.session.add(admin)
        print("Admin user created: admin / admin123")

    # Payment defaults
    if not PaymentSetting.query.filter_by(key="advance_required").first():
        for k, v in [
            ("advance_required", "1"),
            ("advance_percent", "50"),
            ("payment_instructions", "Please pay advance via QR or bank transfer and share the screenshot with us."),
        ]:
            db.session.add(PaymentSetting(key=k, value=v))

    db.session.commit()
    print("Seed complete.")
