"""
Feature 2 — Admin Inventory Update via Email
─────────────────────────────────────────────
Only emails from ADMIN_EMAIL with a subject containing
ADMIN_UPDATE_SUBJECT_KEYWORD are processed here.

Supported email body format (plain text):

    rice stock 2000
    rice cost_price 42
    wheat stock 900
    corn stock 600 cost_price 28

Each line = one product. Fields can be in any order.
Both stock and cost_price are optional per line.

Example email body:
    rice stock 2000 cost_price 45
    wheat stock 1500
    corn cost_price 30
"""

import re

from inventory.inventory_manager import update_inventory
from gmail.email_sender import send_inventory_update_confirmation
from utils.logger import log


# Supported product names (must match inventory.json keys after normalization)
KNOWN_PRODUCTS = {"rice", "wheat", "corn"}


def parse_update_commands(body: str) -> dict:
    """
    Parse the plain-text email body into an updates dict.

    Returns:
        {
            "rice":  { "stock": 2000, "cost_price": 45 },
            "wheat": { "stock": 1500 },
            ...
        }
    """

    updates = {}

    for line in body.splitlines():
        line = line.strip().lower()

        if not line:
            continue

        # Find which product this line refers to
        product_found = None
        for product in KNOWN_PRODUCTS:
            if line.startswith(product):
                product_found = product
                break

        if not product_found:
            continue

        fields = {}

        # Extract stock value if present
        stock_match = re.search(r"stock\s+(\d+(?:\.\d+)?)", line)
        if stock_match:
            fields["stock"] = float(stock_match.group(1))

        # Extract cost_price value if present
        cost_match = re.search(r"cost_price\s+(\d+(?:\.\d+)?)", line)
        if cost_match:
            fields["cost_price"] = float(cost_match.group(1))

        if fields:
            updates[product_found] = fields

    return updates


def handle_admin_inventory_email(sender_email: str, subject: str, body: str):
    """
    Entry point called from main.py when an email from the admin is detected.

    Steps:
    1. Parse the email body for update commands.
    2. Apply updates to inventory.json.
    3. Send a confirmation email back to the admin.
    """

    log(f"Admin inventory update email received from: {sender_email}")

    updates = parse_update_commands(body)

    if not updates:
        log("No valid inventory update commands found in admin email.")
        return

    log(f"Applying inventory updates: {updates}")

    applied = update_inventory(updates)

    if applied:
        log(f"Inventory updated successfully: {applied}")
        send_inventory_update_confirmation(sender_email, applied)
    else:
        log("No changes were applied from admin email.")