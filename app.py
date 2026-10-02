"""Root entrypoint for Vercel Flask detection."""
from wsgi import app

# Vercel looks for `app` in app.py / wsgi.py
__all__ = ["app"]
