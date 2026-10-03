"""Public site branded emails (logo + signature from settings)."""
from __future__ import annotations
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


def _settings():
    try:
        from hotel_site.models.content import HotelSetting
        rows = HotelSetting.query.all()
        return {r.key: r.value for r in rows}
    except Exception:
        return {}


def brand_wrap(body_html: str, title: str = "") -> str:
    s = _settings()
    name = s.get("hotel_name") or "Hotel Grand Garden"
    logo = s.get("logo_url") or ""
    sig = s.get("email_signature") or ""
    phone = s.get("phone") or ""
    email = s.get("email") or ""
    address = s.get("address") or "Urlabari-5, Morang, Nepal"
    logo_html = (
        f'<img src="{logo}" alt="{name}" width="120" style="max-height:72px;width:auto;margin:0 auto 12px;display:block;border-radius:10px;background:#fff;padding:6px">'
        if logo else ""
    )
    sig_html = ""
    if sig:
        if str(sig).startswith("http") or str(sig).startswith("/"):
            sig_html = f'<img src="{sig}" alt="Signature" style="max-height:72px;margin-top:8px">'
        else:
            sig_html = f"<p style='white-space:pre-line;color:#555;margin:8px 0 0'>{sig}</p>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title or name}</title></head>
<body style="margin:0;padding:0;background:#f0f4ef;font-family:'Segoe UI',Arial,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ef;padding:28px 12px">
<tr><td align="center">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 28px rgba(10,22,40,0.08)">
    <tr><td style="height:5px;background:linear-gradient(90deg,#e6392b,#f4c430,#2d8a4e);font-size:0;line-height:0">&nbsp;</td></tr>
    <tr><td style="padding:28px 28px 8px;text-align:center">
      {logo_html}
      <h1 style="margin:0;font-size:22px;color:#0a1628;font-weight:700">{name}</h1>
      <p style="margin:6px 0 0;font-size:13px;color:#5a6a80;letter-spacing:0.04em">Urlabari · Morang · Nepal</p>
      {"<p style='margin:14px 0 0;font-size:15px;color:#1a4b8c;font-weight:600'>" + title + "</p>" if title else ""}
    </td></tr>
    <tr><td style="padding:8px 28px 24px">
      <div style="height:1px;background:linear-gradient(90deg,transparent,#e6392b33,#f4c43066,#2d8a4e33,transparent);margin:0 0 20px"></div>
      <div style="color:#1a1a1a;font-size:15px;line-height:1.6">{body_html}</div>
    </td></tr>
    <tr><td style="padding:0 28px 28px">
      <div style="background:#f7faf5;border-radius:12px;padding:16px 18px;border:1px solid #e8eee6">
        {sig_html}
        <p style="margin:10px 0 0;font-size:12px;color:#5a6a80;line-height:1.5">
          {address}<br>{phone}{" · " + email if email else ""}
        </p>
      </div>
      <p style="margin:16px 0 0;text-align:center;font-size:11px;color:#9aa5b5">
        © {name} · Hotel in Urlabari
      </p>
    </td></tr>
    <tr><td style="height:4px;background:linear-gradient(90deg,#2d8a4e,#f4c430,#e6392b);font-size:0">&nbsp;</td></tr>
  </table>
</td></tr>
</table>
</body></html>"""



def send_email(to_address: str, subject: str, html_body: str, text_fallback: str = "") -> bool:
    if not to_address:
        return False
    server = os.environ.get("MAIL_SERVER") or os.environ.get("SMTP_SERVER")
    port = int(os.environ.get("MAIL_PORT") or os.environ.get("SMTP_PORT") or 587)
    username = os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_USER") or ""
    password = os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD") or ""
    sender = os.environ.get("MAIL_DEFAULT_SENDER") or os.environ.get("MAIL_FROM") or username or "info@hotelgrand.com.np"
    use_tls = (os.environ.get("MAIL_USE_TLS") or "1") not in ("0", "false", "False")

    if not server:
        log.info("MAIL not configured — skip send to %s subject=%s", to_address, subject)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_address
        if text_fallback:
            msg.attach(MIMEText(text_fallback, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(server, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.sendmail(sender, [to_address], msg.as_string())
        return True
    except Exception as e:
        log.warning("email failed: %s", e)
        return False


def notify_booking_received(booking) -> None:
    """Guest: decorative booking-received email. Hotel: info@hotelgrand.com.np."""
    s = _settings()
    hotel_email = (s.get("email") or os.environ.get("HOTEL_EMAIL") or "info@hotelgrand.com.np").strip()
    guest = (
        getattr(booking, "guest_email_display", None)
        or getattr(booking, "guest_email", None)
        or getattr(booking, "email", None)
        or ""
    )
    guest = (guest or "").strip()
    ref = getattr(booking, "booking_ref", None) or str(getattr(booking, "id", ""))
    room = getattr(booking, "room_number", None) or getattr(booking, "room_type_name", None) or ""
    name = getattr(booking, "guest_name", None) or "Guest"
    phone = getattr(booking, "guest_phone", None) or getattr(booking, "phone", None) or ""
    ci = getattr(booking, "check_in", "")
    co = getattr(booking, "check_out", "")

    guest_body = f"""
    <p style="margin:0 0 12px">Dear <strong>{name}</strong>,</p>
    <p style="margin:0 0 12px">Thank you for choosing <strong>Hotel Grand Garden, Urlabari</strong>. We have received your booking request.</p>
    <table role="presentation" width="100%" style="border-collapse:collapse;margin:16px 0;background:#f7faf5;border-radius:12px">
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Reference</td>
          <td style="padding:10px 14px;text-align:right;font-weight:700;color:#0a1628">{ref}</td></tr>
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Room</td>
          <td style="padding:10px 14px;text-align:right;font-weight:600">{room or "—"}</td></tr>
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Check-in</td>
          <td style="padding:10px 14px;text-align:right;font-weight:600">{ci}</td></tr>
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Check-out</td>
          <td style="padding:10px 14px;text-align:right;font-weight:600">{co}</td></tr>
    </table>
    <p style="margin:0;font-size:14px;color:#5a6a80">Our team will confirm shortly. For help, write to <a href="mailto:info@hotelgrand.com.np" style="color:#2d8a4e">info@hotelgrand.com.np</a>.</p>
    """
    if guest:
        ok = send_email(
            guest,
            f"Booking received — {ref} | Hotel Grand Garden",
            brand_wrap(guest_body, "Booking Received"),
            f"Booking {ref} received. Hotel Grand Garden Urlabari.",
        )
        log.info("guest booking mail to %s ok=%s", guest, ok)

    # Always notify hotel
    staff_body = f"""
    <p style="margin:0 0 12px"><strong>New website booking</strong></p>
    <table role="presentation" width="100%" style="border-collapse:collapse;margin:12px 0">
      <tr><td style="padding:8px 0;color:#5a6a80">Ref</td><td style="text-align:right;font-weight:700">{ref}</td></tr>
      <tr><td style="padding:8px 0;color:#5a6a80">Guest</td><td style="text-align:right;font-weight:600">{name}</td></tr>
      <tr><td style="padding:8px 0;color:#5a6a80">Phone</td><td style="text-align:right">{phone or "—"}</td></tr>
      <tr><td style="padding:8px 0;color:#5a6a80">Email</td><td style="text-align:right">{guest or "—"}</td></tr>
      <tr><td style="padding:8px 0;color:#5a6a80">Room</td><td style="text-align:right">{room or "—"}</td></tr>
      <tr><td style="padding:8px 0;color:#5a6a80">Stay</td><td style="text-align:right">{ci} → {co}</td></tr>
    </table>
    <p style="margin:0;font-size:13px;color:#5a6a80">Open HMS → Bookings to confirm or cancel.</p>
    """
    ok2 = send_email(
        hotel_email,
        f"[New Booking] {ref} — {name}",
        brand_wrap(staff_body, "New Booking Alert"),
        f"New booking {ref} by {name}",
    )
    log.info("hotel booking mail to %s ok=%s", hotel_email, ok2)


def notify_booking_status(booking, new_status: str) -> None:
    """Decorative confirmed / cancelled email to guest."""
    guest = (
        getattr(booking, "guest_email_display", None)
        or getattr(booking, "guest_email", None)
        or getattr(booking, "email", None)
        or ""
    )
    guest = (guest or "").strip()
    if not guest:
        return
    ref = getattr(booking, "booking_ref", None) or str(getattr(booking, "id", ""))
    name = getattr(booking, "guest_name", None) or "Guest"
    room = getattr(booking, "room_number", None) or ""
    ci = getattr(booking, "check_in", "")
    co = getattr(booking, "check_out", "")
    status_l = (new_status or "").replace("_", " ").title()
    color = "#2d8a4e" if "confirm" in (new_status or "").lower() else ("#e6392b" if "cancel" in (new_status or "").lower() else "#1a4b8c")
    body = f"""
    <p style="margin:0 0 12px">Dear <strong>{name}</strong>,</p>
    <p style="margin:0 0 16px">Your booking status is now:</p>
    <div style="text-align:center;margin:0 0 18px">
      <span style="display:inline-block;padding:10px 22px;border-radius:999px;background:{color};color:#fff;font-weight:700;letter-spacing:0.04em">{status_l}</span>
    </div>
    <table role="presentation" width="100%" style="border-collapse:collapse;background:#f7faf5;border-radius:12px">
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Reference</td>
          <td style="padding:10px 14px;text-align:right;font-weight:700">{ref}</td></tr>
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Room</td>
          <td style="padding:10px 14px;text-align:right;font-weight:600">{room or "—"}</td></tr>
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Check-in</td>
          <td style="padding:10px 14px;text-align:right">{ci}</td></tr>
      <tr><td style="padding:10px 14px;color:#5a6a80;font-size:13px">Check-out</td>
          <td style="padding:10px 14px;text-align:right">{co}</td></tr>
    </table>
    <p style="margin:16px 0 0;font-size:13px;color:#5a6a80">Questions? <a href="mailto:info@hotelgrand.com.np" style="color:#2d8a4e">info@hotelgrand.com.np</a></p>
    """
    send_email(
        guest,
        f"Booking {status_l} — {ref} | Hotel Grand Garden",
        brand_wrap(body, f"Booking {status_l}"),
        f"Booking {ref}: {status_l}",
    )


def notify_admin_booking(booking) -> None:
    """Email hotel admin when a public booking is created."""
    try:
        s = _settings()
        admin_email = (s.get("email") or os.environ.get("HOTEL_EMAIL") or "info@hotelgrand.com.np").strip() or "info@hotelgrand.com.np"
        # Always also CC primary hotel inbox
        targets = {admin_email, "info@hotelgrand.com.np"}
        ref = getattr(booking, "booking_ref", None) or getattr(booking, "id", "—")
        guest = getattr(booking, "guest_name", None) or getattr(booking, "customer_name", None) or "Guest"
        body = f"""
        <p>New website booking received.</p>
        <ul>
          <li><strong>Ref:</strong> {ref}</li>
          <li><strong>Guest:</strong> {guest}</li>
          <li><strong>Email:</strong> {getattr(booking, 'guest_email', None) or getattr(booking, 'email', '') or '—'}</li>
          <li><strong>Phone:</strong> {getattr(booking, 'guest_phone', None) or getattr(booking, 'phone', '') or '—'}</li>
          <li><strong>Check-in:</strong> {getattr(booking, 'check_in', '')}</li>
          <li><strong>Check-out:</strong> {getattr(booking, 'check_out', '')}</li>
        </ul>
        <p>Open HMS to manage this booking.</p>
        """
        html = brand_wrap(body, title="New booking alert")
        for _to in targets:
            send_email(_to, f"[Booking] {ref} — {guest}", html, text_fallback=f"New booking {ref} by {guest}")
    except Exception as e:
        log.warning("admin booking mail failed: %s", e)
