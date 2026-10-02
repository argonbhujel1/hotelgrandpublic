"""
Direction / routing helpers.
Uses public OSRM demo server for routing (no API key).
User location is never stored.
"""
import requests
from flask import current_app


def get_route(start_lat: float, start_lng: float, mode: str = "driving"):
    """
    Calculate route from user location to hotel.
    mode: 'driving' or 'walking'
    Returns geometry, distance (m), duration (s), or raises.
    """
    dest_lat = current_app.config["HOTEL_LAT"]
    dest_lng = current_app.config["HOTEL_LNG"]

    profile = "driving" if mode == "driving" else "foot"
    # Public OSRM demo – for production consider self-hosted or commercial provider
    url = (
        f"https://router.project-osrm.org/route/v1/{profile}/"
        f"{start_lng},{start_lat};{dest_lng},{dest_lat}"
        f"?overview=full&geometries=geojson"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError("No route found")
        route = data["routes"][0]
        return {
            "geometry": route["geometry"],
            "distance_m": route["distance"],
            "duration_s": route["duration"],
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_min": round(route["duration"] / 60),
            "mode": mode,
        }
    except requests.RequestException as e:
        raise ValueError(f"Routing service unavailable: {e}") from e
