from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify
)
from app.services.content_service import get_hotel_info, get_policies, get_payment_info
from app.services.room_service import get_enabled_room_types, get_room_type_by_slug
from app.services.booking_service import create_booking, get_booking_by_ref
from app.services.room_pricing import calculate_stay
from app.models.room import RoomType
from app import csrf
import os
import uuid
from werkzeug.utils import secure_filename

booking_bp = Blueprint("booking", __name__)

ALLOWED_PROOF = {"png", "jpg", "jpeg", "webp", "gif", "pdf"}


def _client_ip():
    # Respect proxy headers if present
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or ""


def _ip_location(ip: str) -> str:
    """Best-effort geo lookup (free API). Fail soft."""
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return "Local / development"
    try:
        import urllib.request
        import json
        url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "success":
            parts = [data.get("city"), data.get("regionName"), data.get("country"), data.get("isp")]
            return ", ".join(p for p in parts if p)
    except Exception:
        pass
    return "Unknown"


def _save_proof(file_storage):
    if not file_storage or not getattr(file_storage, "filename", None):
        return None
    filename = file_storage.filename
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_PROOF:
        return None
    # Cloudinary for images
    if ext != "pdf":
        try:
            from app.utils.cloudinary_upload import cloudinary_configured, upload_image
            if cloudinary_configured():
                url = upload_image(file_storage, folder="payment_proofs")
                if url:
                    return url
        except Exception:
            pass
    from flask import current_app
    name = f"{uuid.uuid4().hex[:12]}.{ext}"
    folder = os.path.join(current_app.root_path, "static", "images", "payment_proofs")
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, name))
    return f"/static/images/payment_proofs/{name}"


@booking_bp.route("/", methods=["GET", "POST"])
def book():
    hotel = get_hotel_info()
    rooms = get_enabled_room_types()
    policies = get_policies()
    payment = get_payment_info()
    selected_slug = request.args.get("room") or request.form.get("room_slug")

    if request.method == "POST":
        try:
            name = request.form.get("guest_name", "").strip()
            phone = request.form.get("guest_phone", "").strip()
            email = request.form.get("guest_email", "").strip()
            room_type_id = int(request.form.get("room_type_id", 0))
            check_in = datetime.strptime(request.form.get("check_in"), "%Y-%m-%d").date()
            check_out = datetime.strptime(request.form.get("check_out"), "%Y-%m-%d").date()
            num_guests = int(request.form.get("num_guests", 1))
            message = request.form.get("message", "").strip()
            room_id_raw = request.form.get("room_id", "").strip()
            room_id = int(room_id_raw) if room_id_raw else None
            advance_txn = request.form.get("advance_txn_number", "").strip()
            advance_claimed = bool(request.form.get("advance_paid"))
            proof_url = _save_proof(request.files.get("payment_proof"))
            ip = _client_ip()
            loc = _ip_location(ip)

            if payment.get("advance_required"):
                if not advance_claimed:
                    raise ValueError("You must confirm that advance payment has been paid.")
                if not advance_txn or len(advance_txn) < 3:
                    raise ValueError("Transaction / reference number is required after paying advance.")

            booking = create_booking(
                guest_name=name,
                guest_phone=phone,
                guest_email=email,
                room_type_id=room_type_id,
                check_in=check_in,
                check_out=check_out,
                num_guests=num_guests,
                message=message,
                room_id=room_id,
                advance_txn_number=advance_txn,
                advance_paid_claimed=advance_claimed,
                payment_proof_url=proof_url,
                client_ip=ip,
                ip_location=loc,
            )
            return redirect(url_for("booking.confirmation", ref=booking.booking_ref))
        except ValueError as e:
            flash(str(e), "error")
        except Exception:
            flash("Unable to complete booking. Please try again or contact us.", "error")

    return render_template(
        "booking.html",
        hotel=hotel,
        rooms=rooms,
        policies=policies,
        payment=payment,
        selected_slug=selected_slug,
    )


@booking_bp.route("/confirmation/<ref>")
def confirmation(ref):
    hotel = get_hotel_info()
    booking = get_booking_by_ref(ref)
    if not booking:
        flash("Booking not found.", "error")
        return redirect(url_for("booking.book"))
    import json
    nights = json.loads(booking.nightly_rates) if booking.nightly_rates else []
    return render_template(
        "booking_confirmation.html",
        hotel=hotel,
        booking=booking,
        nights=nights,
    )


@booking_bp.route("/quote", methods=["POST"])
@csrf.exempt
def quote():
    """AJAX: server-side price quote for date range + room type."""
    try:
        data = request.get_json() or {}
        room_type_id = int(data.get("room_type_id", 0))
        check_in = datetime.strptime(data.get("check_in"), "%Y-%m-%d").date()
        check_out = datetime.strptime(data.get("check_out"), "%Y-%m-%d").date()
        rt = RoomType.query.get(room_type_id)
        if not rt or not rt.is_enabled:
            return jsonify({"error": "Room not available"}), 400
        pricing = calculate_stay(rt.base_price, check_in, check_out)
        return jsonify(pricing)
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Unable to calculate price"}), 500


@booking_bp.route("/available-rooms", methods=["POST"])
@csrf.exempt
def available_rooms():
    """Return available room numbers for a class + dates."""
    from app.services.room_service import get_available_rooms_for_type
    try:
        data = request.get_json() or {}
        room_type_id = int(data.get("room_type_id", 0))
        check_in = datetime.strptime(data.get("check_in"), "%Y-%m-%d").date()
        check_out = datetime.strptime(data.get("check_out"), "%Y-%m-%d").date()
        rooms = get_available_rooms_for_type(room_type_id, check_in, check_out)
        return jsonify({
            "rooms": [
                {"id": r.id, "room_number": r.room_number, "floor": r.floor or ""}
                for r in rooms
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e), "rooms": []}), 400
