"""Production WSGI entry (Gunicorn, Vercel, Railway, etc.)."""
import os
import sys

# Ensure package import wins (directory app/) over any leftover app.py
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("FLASK_ENV", "production")
    try:
        os.makedirs("/tmp/hotel_grand_instance", exist_ok=True)
    except OSError:
        pass

from app import create_app, db  # app package (folder)

application = create_app()
app = application  # Vercel / Flask look for `app`

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        try:
            app.logger.warning("create_all note: %s", e)
        except Exception:
            pass
