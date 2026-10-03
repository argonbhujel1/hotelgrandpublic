import os
import uuid
from functools import wraps
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, current_app, abort
)
from werkzeug.utils import secure_filename
from hotel_site import db
from hotel_site.models.admin import AdminUser, PaymentSetting
from hotel_site.models.room import RoomType, Room, RoomImage
from hotel_site.models.menu import MenuCategory, MenuItem
from hotel_site.models.content import (
    HotelSetting, Review, Amenity, SeminarHall, OutdoorEvent, PageContent
)
from hotel_site.models.booking import Booking
from hotel_site.models.contact import ContactMessage

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def _safe_count(model):
    try:
        return model.query.count()
    except Exception:
        try:
            from hotel_site import db
            db.session.rollback()
        except Exception:
            pass
        return 0


ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif", "ico", "svg"}


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated


def _upload(file_storage, subfolder="uploads"):
    """Save uploaded image via Cloudinary (preferred) or local static folder."""
    if not file_storage or not getattr(file_storage, "filename", None):
        return None
    filename = file_storage.filename
    if "." not in filename:
        flash("Invalid file name.", "error")
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        flash(f"File type .{ext} not allowed. Use png, jpg, jpeg, webp.", "error")
        return None

    # Prefer Cloudinary when configured (Vercel / production)
    try:
        from hotel_site.utils.cloudinary_upload import cloudinary_configured, upload_image
        if cloudinary_configured():
            url = upload_image(file_storage, folder=subfolder)
            if url:
                return url
            flash("Cloudinary upload failed — check credentials.", "error")
            return None
    except Exception as e:
        current_app.logger.warning("Cloudinary path error: %s", e)

    # Local filesystem fallback (dev)
    name = f"{uuid.uuid4().hex[:12]}.{ext}"
    folder = os.path.join(current_app.root_path, "static", "images", subfolder)
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name)
        file_storage.save(path)
        return f"/static/images/{subfolder}/{name}"
    except Exception as e:
        flash(f"Upload failed: {e}", "error")
        return None


def _get_pay(key, default=""):
    s = PaymentSetting.query.filter_by(key=key).first()
    return s.value if s else default


def _set_pay(key, value):
    s = PaymentSetting.query.filter_by(key=key).first()
    if not s:
        s = PaymentSetting(key=key)
        db.session.add(s)
    s.value = value
    db.session.commit()


def _set_setting(key, value):
    s = HotelSetting.query.filter_by(key=key).first()
    if not s:
        s = HotelSetting(key=key)
        db.session.add(s)
    s.value = value
    db.session.commit()


# ── Auth ──────────────────────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = AdminUser.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            session.permanent = True
            session["admin_id"] = user.id
            session["admin_username"] = user.username
            flash("Welcome back.", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_id", None)
    session.pop("admin_username", None)
    flash("Logged out.", "success")
    return redirect(url_for("admin.login"))


# ── Dashboard ─────────────────────────────────────────

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    stats = {
        "rooms": RoomType.query.count(),
        "bookings": _safe_count(Booking),
        "pending": Booking.query.filter_by(status="pending").count(),
        "messages": ContactMessage.query.filter_by(is_read=False).count(),
        "menu_items": MenuItem.query.count(),
    }
    recent = Booking.query.order_by(Booking.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


# ── Settings / Hero ───────────────────────────────────

@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        for key in ("hotel_name", "tagline", "address", "phone", "email",
                    "check_in", "check_out", "latitude", "longitude"):
            val = request.form.get(key)
            if val is not None:
                _set_setting(key, val.strip())

        # Hero content
        hero = PageContent.query.filter_by(page_key="hero").first()
        if not hero:
            hero = PageContent(page_key="hero")
            db.session.add(hero)
        hero.title = request.form.get("hero_title", "").strip()
        hero.subtitle = request.form.get("hero_subtitle", "").strip()
        hero.body = request.form.get("hero_body", "").strip()
        img = _upload(request.files.get("hero_image"), "hero")
        if img:
            hero.image_url = img
        logo = _upload(request.files.get("logo_image"), "brand")
        if logo:
            _set_setting("logo_url", logo)
            # Also copy to static/images/logo.png for admin sidebar default
            try:
                import shutil
                rel = logo.split("/static/")[-1] if "/static/" in logo else logo.lstrip("/")
                src_path = os.path.join(current_app.root_path, "static", rel)
                if os.path.isfile(src_path):
                    dest = os.path.join(current_app.root_path, "static", "images", "logo.png")
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(src_path, dest)
            except Exception as e:
                current_app.logger.warning("Logo copy failed: %s", e)
        fav = _upload(request.files.get("favicon_image"), "favicon")
        if fav:
            _set_setting("favicon_url", fav)
            try:
                import shutil
                rel = fav.split("/static/")[-1] if "/static/" in fav else fav.lstrip("/")
                src_path = os.path.join(current_app.root_path, "static", rel)
                if os.path.isfile(src_path):
                    fav_dir = os.path.join(current_app.root_path, "static", "favicon")
                    os.makedirs(fav_dir, exist_ok=True)
                    shutil.copy2(src_path, os.path.join(fav_dir, "favicon.ico"))
                    ext = os.path.splitext(src_path)[1] or ".png"
                    shutil.copy2(src_path, os.path.join(fav_dir, "favicon" + ext))
            except Exception as e:
                current_app.logger.warning("Favicon copy failed: %s", e)
        elif logo:
            # no separate favicon — use logo
            _set_setting("favicon_url", logo)
            try:
                import shutil
                rel = logo.split("/static/")[-1] if "/static/" in logo else logo.lstrip("/")
                src_path = os.path.join(current_app.root_path, "static", rel)
                if os.path.isfile(src_path):
                    fav_dir = os.path.join(current_app.root_path, "static", "favicon")
                    os.makedirs(fav_dir, exist_ok=True)
                    shutil.copy2(src_path, os.path.join(fav_dir, "favicon.ico"))
            except Exception as e:
                current_app.logger.warning("Favicon from logo failed: %s", e)
        sig = _upload(request.files.get("email_signature_image"), "brand")
        if sig:
            _set_setting("email_signature", sig)
        # optional text signature fallback
        sig_text = (request.form.get("email_signature_text") or "").strip()
        if sig_text and not sig:
            _set_setting("email_signature", sig_text)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))

    def gs(k, d=""):
        s = HotelSetting.query.filter_by(key=k).first()
        return s.value if s else d

    hero = PageContent.query.filter_by(page_key="hero").first()
    return render_template(
        "admin/settings.html",
        settings={
            "hotel_name": gs("hotel_name", current_app.config["HOTEL_NAME"]),
            "tagline": gs("tagline", current_app.config["HOTEL_TAGLINE"]),
            "address": gs("address", current_app.config["HOTEL_ADDRESS"]),
            "phone": gs("phone", current_app.config["HOTEL_PHONE"]),
            "email": gs("email", current_app.config["HOTEL_EMAIL"]),
            "check_in": gs("check_in", current_app.config["CHECK_IN"]),
            "check_out": gs("check_out", current_app.config["CHECK_OUT"]),
            "latitude": gs("latitude", str(current_app.config["HOTEL_LAT"])),
            "longitude": gs("longitude", str(current_app.config["HOTEL_LNG"])),
            "logo_url": gs("logo_url", ""),
            "email_signature": gs("email_signature", ""),
            "favicon_url": gs("favicon_url", ""),
        },
        hero=hero,
    )


# ── Payment / QR ──────────────────────────────────────

@admin_bp.route("/payment", methods=["GET", "POST"])
@admin_required
def payment():
    if request.method == "POST":
        _set_pay("advance_required", "1" if request.form.get("advance_required") else "0")
        _set_pay("advance_percent", request.form.get("advance_percent", "").strip())
        _set_pay("advance_amount_fixed", request.form.get("advance_amount_fixed", "").strip())
        _set_pay("payment_instructions", request.form.get("payment_instructions", "").strip())
        _set_pay("esewa_id", request.form.get("esewa_id", "").strip())
        _set_pay("khalti_id", request.form.get("khalti_id", "").strip())
        _set_pay("bank_name", request.form.get("bank_name", "").strip())
        _set_pay("bank_account", request.form.get("bank_account", "").strip())
        _set_pay("bank_account_name", request.form.get("bank_account_name", "").strip())
        qr = _upload(request.files.get("qr_image"), "qr")
        if qr:
            _set_pay("qr_image", qr)
        if request.form.get("clear_qr"):
            _set_pay("qr_image", "")
        flash("Payment / QR settings saved.", "success")
        return redirect(url_for("admin.payment"))

    return render_template("admin/payment.html", pay={
        "advance_required": _get_pay("advance_required", "1") == "1",
        "advance_percent": _get_pay("advance_percent", ""),
        "advance_amount_fixed": _get_pay("advance_amount_fixed", "1000"),
        "payment_instructions": _get_pay("payment_instructions", "Please pay advance via QR or bank transfer and share the screenshot."),
        "esewa_id": _get_pay("esewa_id", ""),
        "khalti_id": _get_pay("khalti_id", ""),
        "bank_name": _get_pay("bank_name", ""),
        "bank_account": _get_pay("bank_account", ""),
        "bank_account_name": _get_pay("bank_account_name", ""),
        "qr_image": _get_pay("qr_image", ""),
    })


# ── Room classes (types) ──────────────────────────────

@admin_bp.route("/rooms")
@admin_required
def rooms():
    try:
        from hotel_site import _ensure_public_schema
        _ensure_public_schema()
    except Exception:
        pass

    try:
        types = RoomType.query.order_by(RoomType.sort_order, RoomType.name).all()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        types = []
        flash("Could not load room classes. Tables may still be creating — refresh once.", "error")
    room_counts = {}
    try:
        from hotel_site.models.room import Room
        for rt in types:
            room_counts[rt.id] = Room.query.filter(
                (Room.room_type == rt.name) | (Room.room_type == (rt.slug or ""))
            ).count()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    return render_template("admin/rooms.html", types=types, room_counts=room_counts)


@admin_bp.route("/rooms/type/new", methods=["GET", "POST"])
@admin_bp.route("/rooms/type/<int:type_id>/edit", methods=["GET", "POST"])
@admin_required
def room_type_edit(type_id=None):
    rt = RoomType.query.get(type_id) if type_id else None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
        if not name:
            flash("Name required.", "error")
            return redirect(request.url)
        if not rt:
            rt = RoomType(name=name, slug=slug or name.lower().replace(" ", "-"))
            db.session.add(rt)
        else:
            rt.name = name
            if slug:
                rt.slug = slug
        rt.description = request.form.get("description", "").strip()
        rt.base_price = request.form.get("base_price", 0) or 0
        rt.capacity = int(request.form.get("capacity", 2) or 2)
        rt.amenities = request.form.get("amenities", "").strip()
        # Always enabled — public admin classes are for the website (no manual toggle required)
        rt.is_enabled = True
        rt.sort_order = int(request.form.get("sort_order", 0) or 0)
        db.session.flush()

        # Class image — applies to all rooms of this class
        img = _upload(request.files.get("class_image"), "rooms")
        if img:
            existing = None
            try:
                existing = rt.images.filter_by(is_primary=True).first()
            except Exception:
                existing = None
            if existing:
                existing.image_url = img
                if hasattr(existing, "url"):
                    existing.url = img
            else:
                db.session.add(RoomImage(
                    room_type_id=rt.id, image_url=img, url=img,
                    alt_text=rt.name, alt=rt.name, is_primary=True, sort_order=0
                ))
            # Cascade to all physical rooms of this class
            for room in Room.query.filter(
                (Room.room_type == rt.name) | (Room.room_type == rt.slug)
            ).all():
                room.image_url = img
        db.session.commit()
        flash("Room class saved. Photo applied to all rooms in this class.", "success")
        return redirect(url_for("admin.rooms"))

    return render_template("admin/room_type_form.html", rt=rt)


@admin_bp.route("/rooms/type/<int:type_id>/rooms", methods=["GET", "POST"])
@admin_required
def room_instances(type_id):
    rt = RoomType.query.get_or_404(type_id)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            num = request.form.get("room_number", "").strip()
            if not num:
                flash("Room number required.", "error")
            else:
                try:
                    img = None
                    try:
                        primary = rt.images.filter_by(is_primary=True).first()
                        if not primary:
                            primary = rt.images.first()
                        if primary:
                            img = primary.display_url or primary.image_url or primary.url
                    except Exception:
                        img = None
                    existing = Room.query.filter_by(number=num).first()
                    if existing:
                        # Claim HMS/QR room for this public class (enable website)
                        existing.room_type = rt.name
                        existing.price = rt.base_price or existing.price or 0
                        if rt.description:
                            existing.description = rt.description
                        if rt.amenities:
                            existing.amenities = rt.amenities
                        if img:
                            existing.image_url = img
                        existing.is_active = True
                        existing.show_on_website = True
                        fl = (request.form.get("floor") or "").strip()
                        if fl and hasattr(existing, "floor"):
                            existing.floor = fl
                        if request.form.get("status"):
                            existing.status = request.form.get("status")
                        rt.is_enabled = True
                        db.session.commit()
                        flash(f"Room {num} linked to {rt.name} and shown on website.", "success")
                    else:
                        room_kw = dict(
                            number=num,
                            room_type=rt.name,
                            price=rt.base_price or 0,
                            description=rt.description,
                            amenities=rt.amenities,
                            image_url=img,
                            status=request.form.get("status", "available") or "available",
                            is_active=True,
                            show_on_website=True,
                        )
                        fl = (request.form.get("floor") or "").strip()
                        if fl and hasattr(Room, "floor"):
                            room_kw["floor"] = fl
                        db.session.add(Room(**room_kw))
                        rt.is_enabled = True
                        db.session.commit()
                        flash(f"Room {num} added to {rt.name} (class enabled on website).", "success")
                except Exception as e:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    flash(f"Could not add room: {e}", "error")
        elif action == "update":
            rid = request.form.get("room_id") or "0"
            try:
                rid = int(rid)
            except ValueError:
                rid = 0
            room = Room.query.get(rid)
            if room and (room.room_type == rt.name or room.room_type == (rt.slug or "")):
                room.status = request.form.get("status", room.status) or room.status
                # Checkbox: only sent when checked
                enabled = request.form.get("is_enabled") in ("1", "on", "true", "True")
                room.is_active = True if enabled else room.is_active
                room.show_on_website = enabled
                # Always keep class enabled
                rt.is_enabled = True
                db.session.commit()
                flash("Room updated — website: " + ("On" if enabled else "Off"), "success")
        elif action == "delete":
            rid = request.form.get("room_id") or "0"
            try:
                rid = int(rid)
            except ValueError:
                rid = 0
            room = Room.query.get(rid)
            if room and (room.room_type == rt.name or room.room_type == (rt.slug or "") or True):
                try:
                    from sqlalchemy import text
                    # Detach QR FK so room can be soft-removed
                    db.session.execute(
                        text("UPDATE qr_codes SET is_active = false WHERE room_id = :rid"),
                        {"rid": room.id},
                    )
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                room.show_on_website = False
                room.is_active = False
                room.status = "disabled"
                try:
                    db.session.commit()
                    flash("Room removed from website (QR kept in HMS).", "success")
                except Exception as e:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    flash(f"Could not remove room: {e}", "error")
        return redirect(url_for("admin.room_instances", type_id=type_id))

    rooms = Room.query.filter(
        (Room.room_type == rt.name) | (Room.room_type == (rt.slug or ""))
    ).order_by(Room.number).all()
    # Hide fully disabled from list optional — keep visible so admin can re-enable

    return render_template("admin/room_instances.html", rt=rt, rooms=rooms)


@admin_bp.route("/rooms/type/<int:type_id>/delete", methods=["POST"])
@admin_required
def room_type_delete(type_id):
    rt = RoomType.query.get_or_404(type_id)
    Room.query.filter(Room.room_type == rt.name).delete()
    RoomImage.query.filter_by(room_type_id=rt.id).delete()
    db.session.delete(rt)
    db.session.commit()
    flash("Room class deleted.", "success")
    return redirect(url_for("admin.rooms"))


# ── Bookings ──────────────────────────────────────────

@admin_bp.route("/bookings")
@admin_required
def bookings():
    status = request.args.get("status", "")
    q = Booking.query.order_by(Booking.created_at.desc())
    if status:
        q = q.filter_by(status=status)
    items = q.limit(100).all()
    return render_template("admin/bookings.html", bookings=items, status=status)


@admin_bp.route("/bookings/<int:bid>/status", methods=["POST"])
@admin_required
def booking_status(bid):
    b = Booking.query.get_or_404(bid)
    new_status = request.form.get("status", b.status)
    if new_status in ("pending", "confirmed", "cancelled", "checked_in", "checked_out"):
        b.status = new_status
    pay = request.form.get("payment_status")
    if pay in ("unpaid", "partial", "paid"):
        b.payment_status = pay
    db.session.commit()
    try:
        from hotel_site.services.email_service import notify_booking_status
        notify_booking_status(b, b.status or "")
    except Exception:
        pass
    flash("Booking updated.", "success")
    return redirect(url_for("admin.bookings"))


# ── Menu ──────────────────────────────────────────────


DEFAULT_MENU_CATEGORIES = [
    "Starters & Snacks", "Momo", "Chowmein & Noodles", "Rice & Biryani",
    "Nepali Khana", "Soup", "Chicken", "Mutton & Buff", "Vegetarian",
    "Continental", "Indian", "Breakfast", "Pasta",
    "Tea & Coffee", "Cold Drinks", "Fresh Juice & Mocktails", "Bar", "Cigarette",
]


def _ensure_menu_categories():
    """Create fixed restaurant/bar categories if missing (shared DB safe)."""
    existing = {c.name.strip().lower(): c for c in MenuCategory.query.all()}
    changed = False
    for i, name in enumerate(DEFAULT_MENU_CATEGORIES, 1):
        key = name.lower()
        if key not in existing:
            c = MenuCategory(name=name, slug=name.lower().replace(" ", "-").replace("&", "and"), sort_order=i, is_active=True)
            db.session.add(c)
            changed = True
        else:
            c = existing[key]
            if c.sort_order != i:
                c.sort_order = i
                changed = True
            if hasattr(c, "is_active") and not c.is_active:
                c.is_active = True
                changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

@admin_bp.route("/menu")
@admin_required
def menu():
    try:
        from hotel_site import _ensure_public_schema
        _ensure_public_schema()
    except Exception:
        pass
    try:
        _ensure_menu_categories()
    except Exception:
        pass

    try:
        cats = MenuCategory.query.order_by(MenuCategory.sort_order).all()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        cats = []
        flash(f"Could not load menu categories. Refresh once. ({e})", "error")
    # Preload items as lists so template never hits broken relationship columns
    for c in cats:
        try:
            c._items_list = list(c.items.order_by(MenuItem.sort_order, MenuItem.name).all()) if hasattr(c.items, "order_by") else list(c.items)
        except Exception:
            try:
                db.session.rollback()
                c._items_list = MenuItem.query.filter_by(category_id=c.id).all()
            except Exception:
                c._items_list = []
    return render_template("admin/menu.html", categories=cats)


@admin_bp.route("/menu/category", methods=["POST"])
@admin_required
def menu_category():
    name = request.form.get("name", "").strip()
    if name:
        slug = name.lower().replace(" ", "-")
        db.session.add(MenuCategory(name=name, slug=slug, is_active=True))
        db.session.commit()
        flash("Category added.", "success")
    return redirect(url_for("admin.menu"))


@admin_bp.route("/menu/item", methods=["POST"])
@admin_required
def menu_item():
    """Legacy single-item add — still supported."""
    cat_id = int(request.form.get("category_id", 0) or 0)
    name = (request.form.get("name") or "").strip()
    if cat_id and name:
        try:
            price = float(request.form.get("price") or 0)
        except (TypeError, ValueError):
            price = 0
        prep = request.form.get("prep_time_minutes")
        try:
            prep = int(prep) if prep not in (None, "") else None
        except (TypeError, ValueError):
            prep = None
        item = MenuItem(
            category_id=cat_id,
            name=name,
            description=(request.form.get("description") or "").strip() or None,
            price=price,
            prep_time_minutes=prep,
            is_available=True,
            show_on_website=True,
            show_on_qr=True,
            is_active=True,
        )
        db.session.add(item)
        db.session.commit()
        flash("Menu item added.", "success")
    return redirect(url_for("admin.menu"))


@admin_bp.route("/menu/item/bulk", methods=["POST"])
@admin_required
def menu_item_bulk():
    """Add multiple items at once (name, price, prep time). No image on bulk."""
    cat_id = int(request.form.get("category_id", 0) or 0)
    names = request.form.getlist("names[]") or request.form.getlist("names")
    prices = request.form.getlist("prices[]") or request.form.getlist("prices")
    preps = request.form.getlist("prep_times[]") or request.form.getlist("prep_times")
    if not cat_id:
        flash("Select a category.", "error")
        return redirect(url_for("admin.menu"))
    added = 0
    for i, name in enumerate(names):
        name = (name or "").strip()
        if not name:
            continue
        try:
            price = float(prices[i]) if i < len(prices) and prices[i] not in (None, "") else 0
        except (TypeError, ValueError, IndexError):
            price = 0
        prep = None
        try:
            if i < len(preps) and preps[i] not in (None, ""):
                prep = int(preps[i])
        except (TypeError, ValueError, IndexError):
            prep = None
        item = MenuItem(
            category_id=cat_id,
            name=name,
            price=price,
            prep_time_minutes=prep,
            is_available=True,
            show_on_website=True,
            show_on_qr=True,
            is_active=True,
        )
        db.session.add(item)
        added += 1
    if added:
        db.session.commit()
        flash(f"{added} menu item(s) added. Add photos from Edit if needed.", "success")
    else:
        flash("No items to add (empty names).", "error")
    return redirect(url_for("admin.menu"))


@admin_bp.route("/menu/item/<int:item_id>/toggle", methods=["POST"])
@admin_required
def menu_item_toggle(item_id):
    item = MenuItem.query.get_or_404(item_id)
    field = request.form.get("field", "is_available")
    if field in ("is_available", "show_on_website", "show_on_qr"):
        setattr(item, field, not getattr(item, field))
        db.session.commit()
    return redirect(url_for("admin.menu"))


@admin_bp.route("/menu/item/<int:item_id>/delete", methods=["POST"])
@admin_required
def menu_item_delete(item_id):
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted.", "success")
    return redirect(url_for("admin.menu"))


# ── Reviews ───────────────────────────────────────────

@admin_bp.route("/reviews", methods=["GET", "POST"])
@admin_required
def reviews():
    if request.method == "POST":
        db.session.add(Review(
            author_name=request.form.get("author_name", "").strip(),
            content=request.form.get("content", "").strip(),
            rating=int(request.form.get("rating", 5) or 5),
            is_published=bool(request.form.get("is_published", True)),
        ))
        db.session.commit()
        flash("Review added.", "success")
        return redirect(url_for("admin.reviews"))
    items = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=items)


@admin_bp.route("/reviews/<int:rid>/toggle", methods=["POST"])
@admin_required
def review_toggle(rid):
    r = Review.query.get_or_404(rid)
    r.is_published = not r.is_published
    db.session.commit()
    return redirect(url_for("admin.reviews"))


# ── Messages ──────────────────────────────────────────

@admin_bp.route("/messages")
@admin_required
def messages():
    items = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(50).all()
    return render_template("admin/messages.html", messages=items)


@admin_bp.route("/messages/<int:mid>/read", methods=["POST"])
@admin_required
def message_read(mid):
    m = ContactMessage.query.get_or_404(mid)
    m.is_read = True
    db.session.commit()
    return redirect(url_for("admin.messages"))



# ── Gallery ───────────────────────────────────────────

@admin_bp.route("/gallery", methods=["GET", "POST"])
@admin_required
def gallery():
    import json
    if request.method == "POST":
        action = request.form.get("action", "add")
        s = HotelSetting.query.filter_by(key="gallery_images").first()
        imgs = []
        if s and s.value:
            try:
                imgs = json.loads(s.value)
            except Exception:
                imgs = []
        if action == "add":
            files = request.files.getlist("images")
            for f in files:
                url = _upload(f, "gallery")
                if url:
                    imgs.append(url)
            if not s:
                s = HotelSetting(key="gallery_images")
                db.session.add(s)
            s.value = json.dumps(imgs)
            db.session.commit()
            flash(f"Uploaded {len(files)} image(s).", "success")
        elif action == "delete":
            url = request.form.get("url", "")
            imgs = [u for u in imgs if u != url]
            if not s:
                s = HotelSetting(key="gallery_images")
                db.session.add(s)
            s.value = json.dumps(imgs)
            db.session.commit()
            flash("Image removed.", "success")
        return redirect(url_for("admin.gallery"))
    s = HotelSetting.query.filter_by(key="gallery_images").first()
    imgs = []
    if s and s.value:
        try:
            imgs = json.loads(s.value)
        except Exception:
            imgs = []
    return render_template("admin/gallery.html", images=imgs)


# ── Menu item edit ────────────────────────────────────

@admin_bp.route("/menu/item/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def menu_item_edit(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if request.method == "POST":
        item.name = request.form.get("name", item.name).strip()
        item.description = request.form.get("description", "").strip()
        try:
            item.price = float(request.form.get("price", item.price) or item.price)
        except (TypeError, ValueError):
            pass
        item.show_on_website = bool(request.form.get("show_on_website"))
        item.show_on_qr = bool(request.form.get("show_on_qr"))
        item.is_available = bool(request.form.get("is_available"))
        try:
            pt = request.form.get("prep_time_minutes")
            item.prep_time_minutes = int(pt) if pt not in (None, "") else None
        except (TypeError, ValueError):
            pass
        img = _upload(request.files.get("image"), "menu")
        if img:
            item.image_url = img
        db.session.commit()
        flash("Menu item updated.", "success")
        return redirect(url_for("admin.menu"))
    return render_template("admin/menu_item_edit.html", item=item)


# ── Seminar / Outdoor / Parking ───────────────────────

@admin_bp.route("/events", methods=["GET", "POST"])
@admin_required
def events_admin():
    seminar = SeminarHall.query.first()
    outdoor = OutdoorEvent.query.first()
    if request.method == "POST":
        section = request.form.get("section")
        if section == "seminar":
            if not seminar:
                seminar = SeminarHall()
                db.session.add(seminar)
            seminar.title = request.form.get("s_title", "Seminar Hall").strip()
            seminar.description = request.form.get("s_description", "").strip()
            seminar.capacity = int(request.form.get("s_capacity", 150) or 150)
            seminar.day_rate = request.form.get("s_day_rate", 15000) or 15000
            seminar.hourly_rate = request.form.get("s_hourly_rate", 2000) or 2000
            seminar.is_enabled = bool(request.form.get("s_enabled"))
            img = _upload(request.files.get("s_image"), "events")
            if img:
                seminar.image_url = img
            db.session.commit()
            flash("Seminar hall saved.", "success")
        elif section == "outdoor":
            if not outdoor:
                outdoor = OutdoorEvent()
                db.session.add(outdoor)
            outdoor.title = request.form.get("o_title", "Outdoor Events").strip()
            outdoor.description = request.form.get("o_description", "").strip()
            outdoor.capacity = int(request.form.get("o_capacity", 500) or 500)
            outdoor.features = request.form.get("o_features", "weddings,parties,free parking").strip()
            outdoor.is_enabled = bool(request.form.get("o_enabled"))
            img = _upload(request.files.get("o_image"), "events")
            if img:
                outdoor.image_url = img
            db.session.commit()
            flash("Outdoor events saved.", "success")
        elif section == "parking":
            _set_setting("parking_info", request.form.get("parking_info", "").strip())
            _set_setting("parking_free", "1" if request.form.get("parking_free") else "0")
            img = _upload(request.files.get("parking_image"), "events")
            if img:
                _set_setting("parking_image", img)
            flash("Parking info saved.", "success")
        return redirect(url_for("admin.events_admin"))

    def gs(k, d=""):
        s = HotelSetting.query.filter_by(key=k).first()
        return s.value if s else d

    return render_template(
        "admin/events.html",
        seminar=seminar,
        outdoor=outdoor,
        parking={
            "info": gs("parking_info", "Free on-site parking for hotel guests and event visitors."),
            "free": gs("parking_free", "1") == "1",
            "image": gs("parking_image", ""),
        },
    )



@admin_bp.route("/maintenance", methods=["GET", "POST"])
@admin_required
def maintenance():
    if request.method == "POST":
        enabled = request.form.get("maintenance_mode") in ("1", "on", "true", "True")
        _set_setting("maintenance_mode", "1" if enabled else "0")
        _set_setting("maintenance_message", (request.form.get("maintenance_message") or "").strip())
        logo = _upload(request.files.get("logo_image"), "brand")
        if logo:
            _set_setting("logo_url", logo)
        fav = _upload(request.files.get("favicon_image"), "favicon")
        if fav:
            _set_setting("favicon_url", fav)
        flash("Maintenance settings saved.", "success")
        return redirect(url_for("admin.maintenance"))
    settings = {
        "maintenance_mode": (HotelSetting.query.filter_by(key="maintenance_mode").first() or type("X", (), {"value": "0"})()).value == "1",
        "maintenance_message": (HotelSetting.query.filter_by(key="maintenance_message").first() or type("X", (), {"value": ""})()).value
            or "We are temporarily under maintenance. Please check back soon.",
        "logo_url": (HotelSetting.query.filter_by(key="logo_url").first() or type("X", (), {"value": ""})()).value or "",
        "favicon_url": (HotelSetting.query.filter_by(key="favicon_url").first() or type("X", (), {"value": ""})()).value or "",
    }
    return render_template("admin/maintenance.html", settings=settings)
