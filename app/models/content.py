from datetime import datetime
from app import db


class HotelSetting(db.Model):
    """Key-value settings managed by HMS."""
    __tablename__ = "hotel_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    author_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1-5
    content = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Amenity(db.Model):
    __tablename__ = "amenities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50))  # CSS class or emoji key
    description = db.Column(db.String(255))
    is_enabled = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)


class SeminarHall(db.Model):
    __tablename__ = "seminar_hall"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), default="Seminar Hall")
    description = db.Column(db.Text)
    capacity = db.Column(db.Integer, default=150)
    day_rate = db.Column(db.Numeric(10, 2), default=15000)
    hourly_rate = db.Column(db.Numeric(10, 2), default=2000)
    image_url = db.Column(db.String(500))
    is_enabled = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OutdoorEvent(db.Model):
    __tablename__ = "outdoor_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), default="Outdoor Events")
    description = db.Column(db.Text)
    capacity = db.Column(db.Integer, default=500)
    features = db.Column(db.Text)  # JSON or comma-separated
    image_url = db.Column(db.String(500))
    is_enabled = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PageContent(db.Model):
    """CMS-like content blocks for hero, about, policies, etc."""
    __tablename__ = "page_contents"

    id = db.Column(db.Integer, primary_key=True)
    page_key = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    body = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    extra_json = db.Column(db.Text)  # flexible JSON
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
