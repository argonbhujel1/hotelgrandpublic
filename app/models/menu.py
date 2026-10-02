from datetime import datetime
from app import db


class MenuCategory(db.Model):
    __tablename__ = "menu_categories"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120))
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("MenuItem", back_populates="category", lazy="dynamic")

    @property
    def is_enabled(self):
        return bool(self.is_active)

    @is_enabled.setter
    def is_enabled(self, value):
        self.is_active = bool(value)


class MenuItem(db.Model):
    __tablename__ = "menu_items"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("menu_categories.id"))
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    image_path = db.Column(db.String(255))
    image_url = db.Column(db.String(500))
    is_available = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    is_orderable = db.Column(db.Boolean, default=True)
    show_on_website = db.Column(db.Boolean, default=True)
    show_on_qr = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship("MenuCategory", back_populates="items")

    @property
    def display_image(self):
        return self.image_url or self.image_path or ""
