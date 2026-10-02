"""HMS-shared tables used by public QR ordering (orders, qr_codes, restaurant_tables)."""
from datetime import datetime
from hotel_site import db


class RestaurantTable(db.Model):
    __tablename__ = "restaurant_tables"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    seating_capacity = db.Column(db.Integer, default=4)
    status = db.Column(db.String(20), default="available")
    is_active = db.Column(db.Boolean, default=True)


class QRCode(db.Model):
    __tablename__ = "qr_codes"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    source_type = db.Column(db.String(20), nullable=False)
    room_id = db.Column(db.Integer)
    table_id = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    __tablename__ = "orders"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False)
    source = db.Column(db.String(20), nullable=False)
    room_id = db.Column(db.Integer)
    table_id = db.Column(db.Integer)
    status = db.Column(db.String(30), default="NEW")
    customer_name = db.Column(db.String(120))
    notes = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan", lazy="dynamic")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    menu_item_id = db.Column(db.Integer)
    item_name = db.Column(db.String(150), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)
    notes = db.Column(db.String(255))
