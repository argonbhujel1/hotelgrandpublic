"""
Booking model aligned with HMS `bookings` table + optional public website columns.
Shared Aiven DB: HMS creates core columns; public adds extras via migrate_booking_schema().
"""
from datetime import datetime, date, time
from hotel_site import db


class Booking(db.Model):
    __tablename__ = "bookings"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)

    # --- HMS core ---
    guest_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30))  # HMS name
    email = db.Column(db.String(120))
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), index=True)
    check_in = db.Column(db.DateTime)  # HMS stores DateTime
    check_out = db.Column(db.DateTime)
    num_guests = db.Column(db.Integer, default=1)
    advance_amount = db.Column(db.Numeric(12, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2), default=0)
    payment_status = db.Column(db.String(30), default="pending")
    status = db.Column(db.String(30), default="pending", index=True)
    notes = db.Column(db.Text)
    id_document = db.Column(db.String(100))
    created_by_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Public website extras (added by migrate if missing) ---
    booking_ref = db.Column(db.String(32), index=True)
    guest_phone = db.Column(db.String(30))  # mirror of phone for older public templates
    guest_email = db.Column(db.String(150))
    message = db.Column(db.Text)
    room_type_id = db.Column(db.Integer)
    room_number = db.Column(db.String(20))
    base_price_snapshot = db.Column(db.Numeric(10, 2))
    total_nights = db.Column(db.Integer)
    nightly_rates = db.Column(db.Text)
    source = db.Column(db.String(30), default="website")
    advance_txn_number = db.Column(db.String(100))
    advance_paid_claimed = db.Column(db.Boolean, default=False)
    payment_proof_url = db.Column(db.String(500))
    client_ip = db.Column(db.String(64))
    ip_location = db.Column(db.String(255))

    room = db.relationship("Room", foreign_keys=[room_id])

    # Compatibility properties for templates/services
    @property
    def guest_phone_display(self):
        return self.guest_phone or self.phone or ""

    @property
    def guest_email_display(self):
        return self.guest_email or self.email or ""

    def __repr__(self):
        return f"<Booking {self.booking_ref or self.id}>"


def migrate_booking_schema():
    """Add public columns to HMS bookings table if they do not exist."""
    from sqlalchemy import text, inspect

    extras = [
        ("booking_ref", "VARCHAR(32)"),
        ("guest_phone", "VARCHAR(30)"),
        ("guest_email", "VARCHAR(150)"),
        ("message", "TEXT"),
        ("room_type_id", "INTEGER"),
        ("room_number", "VARCHAR(20)"),
        ("base_price_snapshot", "NUMERIC(10,2)"),
        ("total_nights", "INTEGER"),
        ("nightly_rates", "TEXT"),
        ("source", "VARCHAR(30)"),
        ("advance_txn_number", "VARCHAR(100)"),
        ("advance_paid_claimed", "BOOLEAN DEFAULT FALSE"),
        ("payment_proof_url", "VARCHAR(500)"),
        ("client_ip", "VARCHAR(64)"),
        ("ip_location", "VARCHAR(255)"),
    ]
    try:
        insp = inspect(db.engine)
        if "bookings" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("bookings")}
        with db.engine.begin() as conn:
            for name, typ in extras:
                if name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE bookings ADD COLUMN {name} {typ}"))
                    except Exception:
                        pass
    except Exception:
        pass
