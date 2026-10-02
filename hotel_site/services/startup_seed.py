"""Minimal startup seed — NO auto rooms. Admin adds room classes & rooms."""
from hotel_site import db


def seed_if_empty():
    try:
        _seed_settings()
        _seed_payment_defaults()
        # rooms/menu intentionally NOT seeded — public admin manages them
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _seed_settings():
    from hotel_site.models.content import HotelSetting
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
    from hotel_site.models.admin import PaymentSetting
    defaults = {
        "advance_required": "1",
        "advance_amount_fixed": "1000",
        "advance_percent": "",
        "payment_instructions": "Please pay the advance amount via QR / eSewa / bank and upload the screenshot.",
    }
    for k, v in defaults.items():
        if not PaymentSetting.query.filter_by(key=k).first():
            db.session.add(PaymentSetting(key=k, value=v))
