import json
import os

from config.settings import INVENTORY_PATH

# Cache so we only read the file once per run
_inventory_cache = None


def load_inventory():
    """
    IMPROVEMENT: load inventory from JSON file instead of hardcoded dict.
    Falls back to empty dict if file is missing.
    """
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