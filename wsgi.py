import os
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("FLASK_ENV", "production")
    try:
        os.makedirs("/tmp/hotel_grand_instance", exist_ok=True)
    except OSError:
        pass
from hotel_site import create_app
app = create_app()
application = app
