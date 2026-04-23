import json
import os

from config.settings import INVENTORY_PATH

_inventory_cache = None


def load_inventory():
    global _inventory_cache
    if _inventory_cache is not None:
        return _inventory_cache
    if not os.path.exists(INVENTORY_PATH):
        _inventory_cache = {}
        return _inventory_cache
    with open(INVENTORY_PATH, "r") as f:
        _inventory_cache = json.load(f)
    return _inventory_cache


def reload_inventory():
    global _inventory_cache
    _inventory_cache = None
    return load_inventory()


def save_inventory(data):
    os.makedirs(os.path.dirname(INVENTORY_PATH), exist_ok=True)
    with open(INVENTORY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_available_stock(product):
    product = product.lower().strip()
    return load_inventory().get(product, {}).get("stock", 0)


def get_cost_price(product):
    product = product.lower().strip()
    return load_inventory().get(product, {}).get("cost_price", 0)


def get_min_order(product):
    """Return minimum order quantity for a product (default 1)."""
    product = product.lower().strip()
    return load_inventory().get(product, {}).get("min_order", 1)


def get_low_stock_threshold(product):
    """Return low stock alert threshold (default 100)."""
    product = product.lower().strip()
    return load_inventory().get(product, {}).get("low_stock_threshold", 100)


def update_inventory(updates: dict):
    inventory = load_inventory()
    applied   = {}
    for product, fields in updates.items():
        product = product.lower().strip()
        if product not in inventory:
            inventory[product] = {}
        changed = {}
        for key in ["stock", "cost_price", "min_order", "low_stock_threshold"]:
            if key in fields:
                inventory[product][key] = fields[key]
                changed[key] = fields[key]
        if changed:
            applied[product] = changed
    save_inventory(inventory)
    reload_inventory()
    return applied


def deduct_stock(product: str, quantity: float) -> bool:
    product   = product.lower().strip()
    inventory = load_inventory()
    if product not in inventory:
        return False
    current = inventory[product].get("stock", 0)
    if quantity > current:
        return False
    inventory[product]["stock"] = current - quantity
    save_inventory(inventory)
    reload_inventory()
    return True


def check_low_stock_alerts() -> list[dict]:
    """
    Return list of products currently below their low_stock_threshold.
    Used by the admin panel and pipeline to trigger email alerts.
    """
    inventory = load_inventory()
    alerts    = []
    for product, data in inventory.items():
        stock     = data.get("stock", 0)
        threshold = data.get("low_stock_threshold", 100)
        if stock < threshold:
            alerts.append({
                "product":   product,
                "stock":     stock,
                "threshold": threshold,
            })
    return alerts