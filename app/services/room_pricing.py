"""
Room pricing service – single source of truth for all price calculations.
Monday–Friday: Normal Rate = base_price
Saturday–Sunday: Weekend Offer = base_price - WEEKEND_DISCOUNT
"""
from datetime import date, timedelta
from decimal import Decimal
from flask import current_app


WEEKEND_DISCOUNT = 200  # Rs.


def is_weekend(d: date) -> bool:
    """Saturday=5, Sunday=6. Friday is NOT weekend."""
    return d.weekday() >= 5


def nightly_rate(base_price, d: date) -> Decimal:
    """Return the final rate for a single night date."""
    base = Decimal(str(base_price))
    discount = Decimal(str(current_app.config.get("WEEKEND_DISCOUNT", WEEKEND_DISCOUNT)))
    if is_weekend(d):
        return max(base - discount, Decimal("0"))
    return base


def calculate_stay(base_price, check_in: date, check_out: date) -> dict:
    """
    Calculate total for every actual night from check_in (inclusive)
    to check_out (exclusive).
    Returns dict with nights list, total, etc.
    """
    if check_out <= check_in:
        raise ValueError("Check-out must be after check-in")

    nights = []
    total = Decimal("0")
    current = check_in
    while current < check_out:
        rate = nightly_rate(base_price, current)
        weekend = is_weekend(current)
        nights.append({
            "date": current.isoformat(),
            "rate": float(rate),
            "is_weekend": weekend,
            "label": "Weekend Offer" if weekend else "Normal Rate",
        })
        total += rate
        current += timedelta(days=1)

    return {
        "nights": nights,
        "total_nights": len(nights),
        "total_amount": float(total),
        "base_price": float(Decimal(str(base_price))),
        "weekend_rate": float(nightly_rate(base_price, date(2024, 1, 6))),  # a Saturday
        "normal_rate": float(Decimal(str(base_price))),
    }


def display_rates(base_price) -> dict:
    """Rates for UI cards – normal + weekend offer."""
    base = Decimal(str(base_price))
    discount = Decimal(str(current_app.config.get("WEEKEND_DISCOUNT", WEEKEND_DISCOUNT)))
    weekend = max(base - discount, Decimal("0"))
    return {
        "normal": float(base),
        "weekend": float(weekend),
        "normal_formatted": f"Rs. {base:,.0f}",
        "weekend_formatted": f"Rs. {weekend:,.0f}",
    }
