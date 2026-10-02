"""Production WSGI entry (Gunicorn, Vercel, Railway, etc.)."""
import os

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("FLASK_ENV", "production")
    try:
        os.makedirs("/tmp/hotel_grand_instance", exist_ok=True)
    except OSError:
        pass

from app import create_app, db

app = create_app()

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        try:
            app.logger.warning("create_all note: %s", e)
        except Exception:
            pass

# Aliases some hosts look for
application = app
