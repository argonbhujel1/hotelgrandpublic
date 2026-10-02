from datetime import datetime
from app import db


class Booking(db.Model):
    """Customer room booking – shared with HMS."""
    __tablename__ = "bookings"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    booking_ref = db.Column(db.String(32), unique=True, nullable=False, index=True)

    # Guest
    guest_name = db.Column(db.String(150), nullable=False)
    guest_phone = db.Column(db.String(30), nullable=False)
    guest_email = db.Column(db.String(150))
    num_guests = db.Column(db.Integer, default=1)
    message = db.Column(db.Text)

    # Room
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"))
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"), nullable=True)
    room_number = db.Column(db.String(20))  # snapshot

    # Dates
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)

    # Pricing (stored so historical prices stay correct)
    base_price_snapshot = db.Column(db.Numeric(10, 2), nullable=False)
    total_nights = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    nightly_rates = db.Column(db.Text)  # JSON list of {date, rate, is_weekend}

    # Status
    status = db.Column(db.String(30), default="pending")  # pending, confirmed, cancelled, checked_in, checked_out
    source = db.Column(db.String(30), default="website")
    payment_status = db.Column(db.String(30), default="unpaid")
    advance_txn_number = db.Column(db.String(100))  # guest transaction ID
    advance_paid_claimed = db.Column(db.Boolean, default=False)
    payment_proof_url = db.Column(db.String(500))  # uploaded receipt/screenshot
    client_ip = db.Column(db.String(64))
    ip_location = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    room = db.relationship("Room", foreign_keys=[room_id])
    room_type = db.relationship("RoomType", foreign_keys=[room_type_id])

    def __repr__(self):
        return f"<Booking {self.booking_ref}>"
