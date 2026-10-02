from flask import Blueprint, render_template, request, redirect, url_for, flash
from hotel_site import db
from hotel_site.models.contact import ContactMessage
from hotel_site.services.content_service import get_hotel_info, get_policies

contact_bp = Blueprint("contact", __name__)


@contact_bp.route("/", methods=["GET", "POST"])
def contact():
    hotel = get_hotel_info()
    policies = get_policies()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not message:
            flash("Name and message are required.", "error")
        else:
            try:
                msg = ContactMessage(
                    name=name,
                    email=email or None,
                    phone=phone or None,
                    subject=subject or None,
                    message=message,
                )
                db.session.add(msg)
                db.session.commit()
                flash("Thank you! Your message has been sent. We will contact you soon.", "success")
                return redirect(url_for("contact.contact"))
            except Exception:
                db.session.rollback()
                flash("Unable to send message. Please call or email us directly.", "error")
    return render_template("contact.html", hotel=hotel, policies=policies)
