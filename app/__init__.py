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

    from app.routes.main import main_bp
    from app.routes.rooms import rooms_bp
    from app.routes.booking import booking_bp
    from app.routes.restaurant import restaurant_bp
    from app.routes.contact import contact_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.qr_order import qr_bp

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
    def inject_hotel():
        try:
            from app.services.content_service import get_hotel_info
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
            from app.models.admin import AdminUser
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
            db.create_all()
        except Exception:
            pass
        try:
            ensure_admin_user()
        except Exception:
            pass
        try:
            ensure_booking_columns()
        except Exception:
            pass

    return app
