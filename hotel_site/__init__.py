import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_class=Config):
    # Vercel / Lambda: instance folder must be writable (/tmp)
    instance_path = None
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        instance_path = "/tmp/hotel_grand_instance"
        try:
            os.makedirs(instance_path, exist_ok=True)
        except OSError:
            pass

    app = Flask(
        __name__,
        instance_path=instance_path,
        instance_relative_config=False,
    )
    app.config.from_object(config_class)

    # Ensure instance path is usable even if Flask still touches it
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        app.instance_path = "/tmp/hotel_grand_instance"
        try:
            os.makedirs(app.instance_path, exist_ok=True)
        except OSError:
            pass

    db.init_app(app)
    csrf.init_app(app)

    from hotel_site.routes.main import main_bp
    from hotel_site.routes.rooms import rooms_bp
    from hotel_site.routes.booking import booking_bp
    from hotel_site.routes.restaurant import restaurant_bp
    from hotel_site.routes.contact import contact_bp
    from hotel_site.routes.api import api_bp
    from hotel_site.routes.admin import admin_bp
    from hotel_site.routes.qr_order import qr_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(rooms_bp, url_prefix="/rooms")
    app.register_blueprint(booking_bp, url_prefix="/booking")
    app.register_blueprint(restaurant_bp, url_prefix="/restaurant")
    app.register_blueprint(contact_bp, url_prefix="/contact")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp)
    app.register_blueprint(qr_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.context_processor
    def inject_nepal_time():
        from hotel_site.utils.timeutil import now_npt, format_npt
        return {"now_npt": now_npt, "format_npt": format_npt, "NEPAL_TZ": "Asia/Kathmandu"}

    @app.context_processor
    def inject_admin_brand():
        try:
            from hotel_site.services.content_service import get_setting
            return {
                "admin_logo_url": get_setting("logo_url") or "",
                "admin_favicon_url": get_setting("favicon_url") or get_setting("logo_url") or "",
            }
        except Exception:
            return {"admin_logo_url": "", "admin_favicon_url": ""}

    @app.context_processor
    def inject_hotel():
        try:
            from hotel_site.services.content_service import get_hotel_info
            return {"hotel": get_hotel_info()}
        except Exception:
            from flask import current_app
            return {"hotel": {
                "name": current_app.config.get("HOTEL_NAME", "Hotel Grand"),
                "tagline": current_app.config.get("HOTEL_TAGLINE", ""),
                "phone": current_app.config.get("HOTEL_PHONE", ""),
                "email": current_app.config.get("HOTEL_EMAIL", ""),
                "address": current_app.config.get("HOTEL_ADDRESS", ""),
                "logo_url": "",
            }}

    def ensure_booking_columns():
        """Add new booking columns if missing (safe no-op on shared HMS schema)."""
        from sqlalchemy import text, inspect
        try:
            insp = inspect(db.engine)
            if "bookings" not in insp.get_table_names():
                return
            cols = {c["name"] for c in insp.get_columns("bookings")}
            alters = []
            if "payment_proof_url" not in cols:
                alters.append("ALTER TABLE bookings ADD COLUMN payment_proof_url VARCHAR(500)")
            if "client_ip" not in cols:
                alters.append("ALTER TABLE bookings ADD COLUMN client_ip VARCHAR(64)")
            if "ip_location" not in cols:
                alters.append("ALTER TABLE bookings ADD COLUMN ip_location VARCHAR(255)")
            with db.engine.begin() as conn:
                for sql in alters:
                    try:
                        conn.execute(text(sql))
                    except Exception:
                        pass
        except Exception:
            pass


    def ensure_admin_user():
        """Create/update public admin from Vercel env if set."""
        try:
            from hotel_site.models.admin import AdminUser
            username = (os.environ.get("ADMIN_USERNAME") or "admin").strip()
            password = (os.environ.get("ADMIN_PASSWORD") or "").strip()
            if not password:
                # no password in env — only create default if table empty
                if AdminUser.query.first() is None:
                    u = AdminUser(username=username or "admin", is_active=True)
                    u.set_password("admin123")
                    db.session.add(u)
                    db.session.commit()
                return
            user = AdminUser.query.filter_by(username=username).first()
            if not user:
                user = AdminUser(username=username, is_active=True)
                db.session.add(user)
            user.set_password(password)
            user.is_active = True
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

    with app.app_context():
        try:
            import hotel_site.models  # noqa: F401
            db.create_all()
            _ensure_public_schema()
        except Exception:
            pass
        try:
            ensure_admin_user()
        except Exception:
            pass
        try:
            from hotel_site.services.startup_seed import seed_if_empty
            seed_if_empty()
        except Exception:
            pass
        try:
            from hotel_site.models.booking import migrate_booking_schema
            migrate_booking_schema()
        except Exception:
            pass
        try:
            ensure_booking_columns()
        except Exception:
            pass

    @app.teardown_appcontext
    def _shutdown_session(exception=None):
        try:
            db.session.remove()
        except Exception:
            pass


    @app.before_request
    def maintenance_gate():
        from flask import request, session, render_template_string
        ep = request.endpoint or ""
        if ep.startswith("static") or ep.startswith("admin"):
            return
        try:
            from hotel_site.services.content_service import get_setting
            if get_setting("maintenance_mode") == "1":
                msg = get_setting("maintenance_message") or "We are under maintenance. Please check back soon."
                logo = get_setting("logo_url") or ""
                fav = get_setting("favicon_url") or logo or ""
                return render_template_string(
                    """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
                    <title>Maintenance | Hotel Grand Garden Urlabari</title>
                    {% if fav %}<link rel="icon" href="{{ fav }}">{% endif %}
                    <style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
                    font-family:system-ui,sans-serif;background:linear-gradient(160deg,#0f172a,#1e293b);color:#f8fafc;text-align:center;padding:24px}
                    img{max-height:80px;margin-bottom:20px;border-radius:12px;background:#fff;padding:8px}
                    h1{font-size:1.75rem;margin:0 0 12px}p{opacity:.9;max-width:420px;line-height:1.5}</style></head>
                    <body>{% if logo %}<div><img src="{{ logo }}" alt="Hotel Grand Garden"></div>{% endif %}
                    <div><h1>Under Maintenance</h1><p>{{ msg }}</p>
                    <p style="margin-top:28px;font-size:.85rem;opacity:.6">Hotel Grand Garden · Urlabari, Morang</p></div></body></html>""",
                    msg=msg, logo=logo, fav=fav,
                ), 503
        except Exception:
            pass


    with app.app_context():
        try:
            from hotel_site.models.content import HotelSetting
            from hotel_site import db as _db
            row = HotelSetting.query.filter_by(key="email").first()
            if row:
                row.value = "info@hotelgrand.com.np"
            else:
                _db.session.add(HotelSetting(key="email", value="info@hotelgrand.com.np"))
            _db.session.commit()
        except Exception:
            try:
                from hotel_site import db as _db
                _db.session.rollback()
            except Exception:
                pass

    return app


def _ensure_public_schema():
    from sqlalchemy import text
    patches = [
        "ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS slug VARCHAR(120)",
        "ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_orderable BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS show_on_website BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS show_on_qr BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT TRUE",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0",
        "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS prep_time_minutes INTEGER",
        "ALTER TABLE room_types ADD COLUMN IF NOT EXISTS slug VARCHAR(140)",
        "ALTER TABLE room_types ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE room_types ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0",
        "ALTER TABLE room_types ADD COLUMN IF NOT EXISTS base_price NUMERIC(10,2) DEFAULT 0",
        "ALTER TABLE room_types ADD COLUMN IF NOT EXISTS capacity INTEGER DEFAULT 2",
        "ALTER TABLE room_types ADD COLUMN IF NOT EXISTS amenities TEXT",
        "ALTER TABLE room_types ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE room_images ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
        "ALTER TABLE room_images ADD COLUMN IF NOT EXISTS url VARCHAR(500)",
        "ALTER TABLE room_images ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS show_on_website BOOLEAN DEFAULT TRUE",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS floor VARCHAR(20)",
    ]
    for sql in patches:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
