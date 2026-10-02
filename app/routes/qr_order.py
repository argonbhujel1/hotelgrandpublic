"""Guest QR ordering on public site — orders land in HMS shared tables."""
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, abort
from app import db, csrf
from app.models.hms_shared import QRCode, Order, OrderItem, RestaurantTable
from app.models.menu import MenuItem, MenuCategory
from app.models.room import Room
from app.services.menu_service import get_qr_menu

qr_bp = Blueprint("qr", __name__)


def _resolve_token(token: str):
    qr = QRCode.query.filter_by(token=token, is_active=True).first()
    if not qr:
        return None
    label = "Order"
    source = "COUNTER"
    room_id = table_id = None
    if qr.source_type == "room" and qr.room_id:
        room = db.session.get(Room, qr.room_id)
        if room:
            label = f"Room {room.number}"
            source = "ROOM"
            room_id = room.id
    elif qr.source_type == "table" and qr.table_id:
        table = db.session.get(RestaurantTable, qr.table_id)
        if table:
            label = f"Table {table.number}"
            source = "TABLE"
            table_id = table.id
    return {"qr": qr, "label": label, "source": source, "room_id": room_id, "table_id": table_id}


@qr_bp.route("/qr/<token>")
def order_page(token):
    ctx = _resolve_token(token)
    if not ctx:
        abort(404)
    menu = get_qr_menu()
    return render_template(
        "qr_order.html",
        token=token,
        label=ctx["label"],
        source=ctx["source"],
        menu=menu,
    )


@qr_bp.route("/qr/<token>/submit", methods=["POST"])
@csrf.exempt
def submit_order(token):
    ctx = _resolve_token(token)
    if not ctx:
        return jsonify({"ok": False, "error": "Invalid or expired QR"}), 404
    data = request.get_json(silent=True) or {}
    items_raw = data.get("items") or []
    if not items_raw:
        return jsonify({"ok": False, "error": "Cart is empty"}), 400
    customer = (data.get("customer_name") or "").strip() or None
    notes = (data.get("notes") or "").strip() or None

    # order number
    last = Order.query.order_by(Order.id.desc()).first()
    n = (last.id + 1) if last else 1
    order_number = f"HG-{n:05d}"

    subtotal = Decimal("0")
    order = Order(
        order_number=order_number,
        source=ctx["source"],
        room_id=ctx["room_id"],
        table_id=ctx["table_id"],
        status="NEW",
        customer_name=customer,
        notes=notes,
        subtotal=0,
    )
    db.session.add(order)
    db.session.flush()

    for row in items_raw:
        mid = int(row.get("id") or 0)
        qty = max(1, int(row.get("qty") or 1))
        mi = db.session.get(MenuItem, mid)
        if not mi or not mi.is_available or not mi.is_active:
            continue
        line = (mi.price or 0) * qty
        subtotal += Decimal(str(line))
        db.session.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=mi.id,
                item_name=mi.name,
                unit_price=mi.price,
                quantity=qty,
                line_total=line,
                notes=row.get("notes"),
            )
        )
    if subtotal <= 0:
        db.session.rollback()
        return jsonify({"ok": False, "error": "No valid items"}), 400
    order.subtotal = subtotal
    db.session.commit()
    return jsonify({
        "ok": True,
        "order_number": order_number,
        "message": f"Order {order_number} sent to kitchen. Thank you!",
    })
