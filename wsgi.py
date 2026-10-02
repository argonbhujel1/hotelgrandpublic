"""Vercel / production WSGI entrypoint."""
import os

if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("FLASK_ENV", "production")
    try:
        os.makedirs("/tmp/hotel_grand_instance", exist_ok=True)
    except OSError:
        pass

from app import create_app as _create_flask_app

_flask = _create_flask_app()
if not hasattr(_flask, "wsgi_app"):
    raise RuntimeError("create_app() did not return Flask app, got %r" % (type(_flask),))

app = _flask
application = _flask
