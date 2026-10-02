"""Menu helpers for website and QR ordering on public site."""


class _MenuCatView:
    """Lightweight view so templates can use cat.name and cat['items']."""

    def __init__(self, category, items):
        self.id = category.id if category else None
        self.name = category.name if category else "Menu"
        self.description = getattr(category, "description", None) if category else None
        self._items = items

    def __getitem__(self, key):
        if key == "items":
            return self._items
        raise KeyError(key)

    @property
    def items(self):
        return self._items


class _MenuItemView:
    def __init__(self, item):
        self.id = item.id
        self.name = item.name
        self.description = item.description
        self.price = item.price
        self.image_url = getattr(item, "display_image", None) or item.image_url or item.image_path or ""
        try:
            self.price_formatted = f"Rs. {float(item.price):,.0f}"
        except Exception:
            self.price_formatted = f"Rs. {item.price}"


def get_website_menu():
    """Categories with items shown on website."""
    try:
        from app.models.menu import MenuCategory, MenuItem
        cats = (
            MenuCategory.query.filter_by(is_active=True)
            .order_by(MenuCategory.sort_order, MenuCategory.name)
            .all()
        )
        result = []
        for c in cats:
            items = (
                MenuItem.query.filter_by(category_id=c.id, is_active=True, show_on_website=True)
                .order_by(MenuItem.sort_order, MenuItem.name)
                .all()
            )
            if not items:
                items = (
                    MenuItem.query.filter_by(category_id=c.id, is_available=True)
                    .order_by(MenuItem.sort_order, MenuItem.name)
                    .all()
                )
            if items:
                result.append(_MenuCatView(c, [_MenuItemView(i) for i in items]))
        return result
    except Exception:
        return []


def get_qr_menu():
    """Categories + items for QR order page (show_on_qr)."""
    try:
        from app.models.menu import MenuCategory, MenuItem
        cats = (
            MenuCategory.query.filter_by(is_active=True)
            .order_by(MenuCategory.sort_order, MenuCategory.name)
            .all()
        )
        menu = []
        for c in cats:
            items = (
                MenuItem.query.filter_by(
                    category_id=c.id,
                    is_active=True,
                    is_available=True,
                    show_on_qr=True,
                )
                .order_by(MenuItem.sort_order, MenuItem.name)
                .all()
            )
            if items:
                menu.append({"category": c, "items": items})
        if not menu:
            items = (
                MenuItem.query.filter_by(is_active=True, is_available=True)
                .order_by(MenuItem.sort_order, MenuItem.name)
                .all()
            )
            if items:
                menu.append({"category": None, "items": items})
        return menu
    except Exception:
        return []
