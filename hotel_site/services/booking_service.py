import json
import secrets
from datetime import date, datetime
from decimal import Decimal
from hotel_site import db
from hotel_site.models.booking import Booking
from hotel_site.models.room import RoomType
from hotel_site.services.room_service import get_available_rooms_for_type, compute_pricing


def generate_booking_ref() -> str:
    return "HG" + secrets.token_hex(4).upper()


def create_booking(
    guest_name: str,
    guest_phone: str,
    guest_email: str,
    room_type_id: int,
    check_in: date,
    check_out: date,
    num_guests: int = 1,
    message: str = "",
    room_id: int = None,
    advance_txn_number: str = "",
    advance_paid_claimed: bool = False,
    payment_proof_url: str = None,
    client_ip: str = None,
    ip_location: str = None,
) -> Booking:
    """Server-side validated booking creation with recalculated pricing."""
    if not guest_name or not guest_phone:
        raise ValueError("Name and phone are required")
    if check_out <= check_in:
        raise ValueError("Check-out must be after check-in")
    if check_in < date.today():
        raise ValueError("Check-in cannot be in the past")
    if num_guests < 1:
        raise ValueError("At least one guest is required")

    rt = RoomType.query.get(room_type_id)
    if not rt or not rt.is_enabled:
        raise ValueError("Selected room type is not available")

    if num_guests > (rt.capacity or 10):
        raise ValueError(f"Maximum capacity for this room is {rt.capacity}")

    available = get_available_rooms_for_type(room_type_id, check_in, check_out)
    if not available:
        raise ValueError("No rooms available for the selected dates")

    pricing = compute_pricing(room_type_id, check_in, check_out)
    room = None
    if room_id:
        for r in available:
            if r.id == room_id:
                room = r
                break
        if not room:
            raise ValueError("Selected room is not available for these dates")
    else:
        room = available[0]

    from datetime import datetime, time
    # HMS stores check_in/out as DateTime
    ci_dt = check_in if isinstance(check_in, datetime) else datetime.combine(check_in, time(12, 0))
    co_dt = check_out if isinstance(check_out, datetime) else datetime.combine(check_out, time(11, 0))
    phone_val = guest_phone.strip()
    email_val = (guest_email or "").strip() or None
    # Fixed advance amount from payment settings if claimed
    adv_amt = Decimal("0")
    if advance_paid_claimed:
        try:
            from hotel_site.models.admin import PaymentSetting
            row = PaymentSetting.query.filter_by(key="advance_amount_fixed").first()
            if row and row.value:
                adv_amt = Decimal(str(row.value))
        except Exception:
            adv_amt = Decimal("0")

    booking = Booking(
        booking_ref=generate_booking_ref(),
        guest_name=guest_name.strip(),
        phone=phone_val,
        email=email_val,
        guest_phone=phone_val,
        guest_email=email_val,
        num_guests=num_guests,
        message=(message or "").strip() or None,
        notes=(message or "").strip() or None,
        room_id=room.id,
        room_type_id=rt.id,
        room_number=getattr(room, "room_number", None) or room.number,
        check_in=ci_dt,
        check_out=co_dt,
        base_price_snapshot=Decimal(str(rt.base_price)),
        total_nights=pricing["total_nights"],
        total_amount=Decimal(str(pricing["total_amount"])),
        advance_amount=adv_amt,
        nightly_rates=json.dumps(pricing["nights"]),
        status="pending",
        source="website",
        payment_status="partial" if advance_paid_claimed else "unpaid",
        advance_txn_number=(advance_txn_number or "").strip() or None,
        advance_paid_claimed=bool(advance_paid_claimed),
        payment_proof_url=payment_proof_url or None,
        client_ip=(client_ip or "").strip() or None,
        ip_location=(ip_location or "").strip() or None,
    )
    db.session.add(booking)
    db.session.commit()
    try:
        from hotel_site.services.email_service import notify_booking_received
        notify_booking_received(booking)
    except Exception:
        pass
    return booking


def get_booking_by_ref(ref: str):
    return Booking.query.filter_by(booking_ref=ref).first()
