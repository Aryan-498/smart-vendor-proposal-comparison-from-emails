import json
import os

from config.settings import INVENTORY_PATH

# In-memory cache — reset with reload_inventory() after any write
_inventory_cache = None


def load_inventory():
    """Load inventory from JSON file. Uses cache after first load."""

    global _inventory_cache

    if _inventory_cache is not None:
        return _inventory_cache

    if not os.path.exists(INVENTORY_PATH):
        print(f"Warning: inventory file not found at {INVENTORY_PATH}")
        _inventory_cache = {}
        return _inventory_cache

    with open(INVENTORY_PATH, "r") as f:
        _inventory_cache = json.load(f)

    return _inventory_cache


def reload_inventory():
    """Force reload from disk (used after an update is written)."""

    global _inventory_cache
    _inventory_cache = None
    return load_inventory()


def save_inventory(data):
    """Write inventory dict back to the JSON file."""

    os.makedirs(os.path.dirname(INVENTORY_PATH), exist_ok=True)

    with open(INVENTORY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_available_stock(product):

    product = product.lower().strip()
    inventory = load_inventory()

    if product not in inventory:
        return 0

    return inventory[product].get("stock", 0)


def get_cost_price(product):

    product = product.lower().strip()
    inventory = load_inventory()

    if product not in inventory:
        return 0

    return inventory[product].get("cost_price", 0)


def update_inventory(updates: dict):
    """
    Feature 2 — Apply stock and/or cost_price updates to inventory.json.

    updates format:
    {
        "rice":  { "stock": 2000, "cost_price": 42 },
        "wheat": { "stock": 900 }
    }

    Returns a dict of only the fields that were actually changed.
    """

    inventory = load_inventory()
    applied = {}

    for product, fields in updates.items():
        product = product.lower().strip()

        if product not in inventory:
            inventory[product] = {}

        changed = {}

        if "stock" in fields:
            inventory[product]["stock"] = fields["stock"]
            changed["stock"] = fields["stock"]

        if "cost_price" in fields:
            inventory[product]["cost_price"] = fields["cost_price"]
            changed["cost_price"] = fields["cost_price"]

        if changed:
            applied[product] = changed

    save_inventory(inventory)
    reload_inventory()

    return applied