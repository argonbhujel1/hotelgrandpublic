from datetime import datetime
from hotel_site import db


class RoomType(db.Model):
    __tablename__ = "room_types"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140))
    description = db.Column(db.Text)
    base_price = db.Column(db.Numeric(10, 2), default=0)
    capacity = db.Column(db.Integer, default=2)
    amenities = db.Column(db.Text)
    is_enabled = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship("RoomImage", back_populates="room_type", lazy="dynamic")


class RoomImage(db.Model):
    __tablename__ = "room_images"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"))
    url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))  # admin uses this name
    alt = db.Column(db.String(200))
    alt_text = db.Column(db.String(200))
    is_primary = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)

    room_type = db.relationship("RoomType", back_populates="images")

    @property
    def display_url(self):
        return self.image_url or self.url or ""


class Room(db.Model):
    """HMS-compatible rooms row."""
    __tablename__ = "rooms"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True)
    room_type = db.Column(db.String(50))
    price = db.Column(db.Numeric(12, 2), default=0)
    description = db.Column(db.Text)
    amenities = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default="available")
    is_active = db.Column(db.Boolean, default=True)
    show_on_website = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def display_image(self):
        return self.image_url or self.image_path or ""

    @property
    def room_number(self):
        return self.number
