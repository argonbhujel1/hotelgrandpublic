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
    address = s.get("address") or ""
    logo_html = f'<img src="{logo}" alt="{name}" style="max-height:64px;margin-bottom:12px">' if logo else ""
    sig_html = ""
    if sig:
        if sig.startswith("http") or sig.startswith("/"):
            sig_html = f'<img src="{sig}" alt="Signature" style="max-height:80px;margin-top:8px">'
        else:
            sig_html = f"<p style='white-space:pre-line;color:#555'>{sig}</p>"
    return f"""<!DOCTYPE html><html><body style="font-family:Segoe UI,Arial,sans-serif;background:#f6f7f9;padding:24px">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;padding:28px;border:1px solid #e8e8e8">
  <div style="text-align:center">{logo_html}<h2 style="margin:0;color:#1a1a1a">{name}</h2>
  <p style="color:#666;margin:4px 0 20px;font-size:14px">{title}</p></div>
  <div style="color:#333;line-height:1.55;font-size:15px">{body_html}</div>
  <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
  <div style="font-size:13px;color:#666">
    {sig_html}
    <p style="margin:8px 0 0">{address}<br>{phone}<br>{email}</p>
  </div>
</div></body></html>"""


def send_email(to_address: str, subject: str, html_body: str, text_fallback: str = "") -> bool:
    if not to_address:
        return False
    server = os.environ.get("MAIL_SERVER") or os.environ.get("SMTP_SERVER")
    port = int(os.environ.get("MAIL_PORT") or os.environ.get("SMTP_PORT") or 587)
    username = os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_USER") or ""
    password = os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD") or ""
    sender = os.environ.get("MAIL_DEFAULT_SENDER") or os.environ.get("MAIL_FROM") or username or "noreply@hotelgrand.com.np"
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
    s = _settings()
    hotel_email = s.get("email") or os.environ.get("HOTEL_EMAIL") or ""
    guest = booking.guest_email_display or getattr(booking, "email", None) or ""
    ref = booking.booking_ref or str(booking.id)
    room = booking.room_number or ""
    body = f"""
    <p>Dear <strong>{booking.guest_name}</strong>,</p>
    <p>We have received your booking request.</p>
    <ul>
      <li><strong>Reference:</strong> {ref}</li>
      <li><strong>Room:</strong> {room}</li>
      <li><strong>Check-in:</strong> {booking.check_in}</li>
      <li><strong>Check-out:</strong> {booking.check_out}</li>
      <li><strong>Guests:</strong> {booking.num_guests}</li>
      <li><strong>Status:</strong> Pending confirmation</li>
    </ul>
    <p>Our team will review and confirm shortly. Thank you for choosing Hotel Grand Garden.</p>
    """
    html = brand_wrap(body, "Booking Received")
    if guest:
        send_email(guest, f"Booking received — {ref}", html, f"Booking {ref} received.")
    if hotel_email:
        staff_body = body + f"<p>Guest phone: {booking.guest_phone_display or booking.phone}</p>"
        send_email(hotel_email, f"New website booking — {ref}", brand_wrap(staff_body, "New Booking"), f"New booking {ref}")


def notify_booking_status(booking, new_status: str) -> None:
    guest = booking.guest_email_display or getattr(booking, "email", None) or ""
    if not guest:
        return
    ref = booking.booking_ref or str(booking.id)
    body = f"""
    <p>Dear <strong>{booking.guest_name}</strong>,</p>
    <p>Your booking <strong>{ref}</strong> status is now: <strong>{new_status.replace('_',' ').title()}</strong>.</p>
    <p>Room: {booking.room_number or '—'} · Check-in: {booking.check_in} · Check-out: {booking.check_out}</p>
    """
    send_email(guest, f"Booking {new_status} — {ref}", brand_wrap(body, "Booking Update"), f"Booking {ref}: {new_status}")


def notify_admin_booking(booking) -> None:
    """Email hotel admin when a public booking is created."""
    try:
        s = _settings()
        admin_email = (s.get("email") or "").strip()
        if not admin_email:
            return
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
        send_email(admin_email, f"[Booking] {ref} — {guest}", html, text_fallback=f"New booking {ref} by {guest}")
    except Exception as e:
        log.warning("admin booking mail failed: %s", e)
