from hotel_site import csrf
from flask import Blueprint, request, jsonify, current_app
from hotel_site.services.direction_service import get_route

api_bp = Blueprint("api", __name__)


@api_bp.route("/route", methods=["POST"])
@csrf.exempt
def route():
    """
    Calculate route from user coords to hotel.
    Body: { lat, lng, mode: 'driving'|'walking' }
    Never stores user location.
    """
    try:
        data = request.get_json() or {}
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
        mode = data.get("mode", "driving")
        if mode not in ("driving", "walking"):
            mode = "driving"
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        result = get_route(lat, lng, mode)
        return jsonify({
            "ok": True,
            "geometry": result["geometry"],
            "distance_km": result["distance_km"],
            "duration_min": result["duration_min"],
            "mode": result["mode"],
            "destination": {
                "name": current_app.config["HOTEL_NAME"],
                "lat": current_app.config["HOTEL_LAT"],
                "lng": current_app.config["HOTEL_LNG"],
            },
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Route calculation failed. Please try again."}), 500


@api_bp.route("/hotel-location")
def hotel_location():
    return jsonify({
        "name": current_app.config["HOTEL_NAME"],
        "address": current_app.config["HOTEL_ADDRESS"],
        "lat": current_app.config["HOTEL_LAT"],
        "lng": current_app.config["HOTEL_LNG"],
        "phone": current_app.config["HOTEL_PHONE"],
    })
