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
    s = _settings()
    hotel_email = s.get("email") or os.environ.get("HOTEL_EMAIL") or "info@hotelgrand.com.np"
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
        admin_email = (s.get("email") or os.environ.get("HOTEL_EMAIL") or "info@hotelgrand.com.np").strip()
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
