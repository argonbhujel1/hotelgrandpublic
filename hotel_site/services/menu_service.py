from hotel_site.models.menu import MenuCategory, MenuItem


def get_website_menu():
    """Categories + items marked for website (shared HMS tables)."""
    cats = (
        MenuCategory.query.filter_by(is_active=True)
        .order_by(MenuCategory.sort_order, MenuCategory.name)
        .all()
    )
    result = []
    for c in cats:
        items = (
            MenuItem.query.filter_by(
                category_id=c.id, is_active=True, is_available=True, show_on_website=True
            )
            .order_by(MenuItem.sort_order, MenuItem.name)
            .all()
        )
        # also include items without category filter if needed
        if items:
            result.append({"category": c, "items": items})
    # Uncategorized website items
    uncat = (
        MenuItem.query.filter(
            MenuItem.category_id.is_(None),
            MenuItem.is_active == True,
            MenuItem.is_available == True,
            MenuItem.show_on_website == True,
        )
        .order_by(MenuItem.sort_order, MenuItem.name)
        .all()
    )
    if uncat:
        result.append({"category": type("C", (), {"id": 0, "name": "Specials"})(), "items": uncat})
    return result


def get_qr_menu():
    cats = (
        MenuCategory.query.filter_by(is_active=True)
        .order_by(MenuCategory.sort_order, MenuCategory.name)
        .all()
    )
    result = []
    for c in cats:
        items = (
            MenuItem.query.filter_by(
                category_id=c.id, is_active=True, is_available=True, show_on_qr=True
            )
            .order_by(MenuItem.sort_order, MenuItem.name)
            .all()
        )
        if items:
            result.append({"category": c, "items": items})
    return result
