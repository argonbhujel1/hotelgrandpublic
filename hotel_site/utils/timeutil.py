"""Nepal Standard Time (NPT, UTC+5:45)."""
from datetime import datetime, timezone, timedelta

NPT = timezone(timedelta(hours=5, minutes=45))  # Asia/Kathmandu


def now_npt() -> datetime:
    return datetime.now(NPT)


def utc_to_npt(dt: datetime) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(NPT)


def format_npt(dt, fmt="%d %b %Y, %I:%M %p") -> str:
    if dt is None:
        return "—"
    try:
        local = utc_to_npt(dt) if getattr(dt, "tzinfo", None) is not None or True else dt
        if getattr(dt, "tzinfo", None) is None:
            # treat naive DB times as UTC then convert
            local = dt.replace(tzinfo=timezone.utc).astimezone(NPT)
        return local.strftime(fmt) + " NPT"
    except Exception:
        try:
            return dt.strftime(fmt)
        except Exception:
            return str(dt)


def npt_now_naive() -> datetime:
    """Naive datetime in NPT wall-clock (for storing local Nepal time)."""
    return now_npt().replace(tzinfo=None)
