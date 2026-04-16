import math

from database.db_manager import get_connection
from processing.normalization import normalize_product
from processing.intent_filter import intent_score
from processing.profit_calculator import calculate_profit, profit_score
from inventory.inventory_manager import get_available_stock


def get_max_vendor_orders():
    """Fetch the maximum total_orders across all vendors for normalization."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(total_orders) FROM vendors")

    row = cursor.fetchone()

    conn.close()

    if not row or row[0] is None:
        return 1

    return max(row[0], 1)


def get_vendor_score(vendor):
    """
    BUG FIX: previously returned math.log(1 + total_orders) which is unbounded.
    A vendor with 1000 orders scored ~6.9 while all other components cap at 1.0,
    causing vendor weight to dominate completely.

    Fix: normalize using log(1 + orders) / log(1 + max_orders) → always 0.0–1.0.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT total_orders FROM vendors WHERE name = ?", (vendor,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return 0.0

    total_orders = row[0]
    max_orders = get_max_vendor_orders()

    # BUG FIX: normalize to 0–1 range
    return math.log(1 + total_orders) / math.log(1 + max_orders)


def rank_offers(product):

    product = normalize_product(product)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT product, quantity, unit, price, vendor, intent FROM offers"
    )

    rows = cursor.fetchall()

    conn.close()

    product_rows = [
        row for row in rows
        if normalize_product(row[0]) == product
    ]

    if not product_rows:
        return None

    # inventory filter: only keep offers within available stock
    available_stock = get_available_stock(product)

    valid_rows = [
        row for row in product_rows
        if row[1] <= available_stock
    ]

    if not valid_rows:
        return None

    profits = [calculate_profit(product, row[3]) for row in valid_rows]

    max_profit = max(profits) if profits else 1
    max_quantity = max(row[1] for row in valid_rows)

    offers = []

    for row in valid_rows:

        p, quantity, unit, price, vendor, intent = row

        profit = calculate_profit(p, price)

        p_score = profit_score(profit, max_profit)

        quantity_score = quantity / max_quantity if max_quantity else 0

        vendor_sc = get_vendor_score(vendor)  # now properly 0–1

        intent_sc = intent_score(intent)

        score = (
            0.4 * p_score +
            0.3 * quantity_score +
            0.2 * vendor_sc +
            0.1 * intent_sc
        )

        offers.append({
            "vendor": vendor,
            "product": p,
            "price": price,
            "quantity": quantity,
            "score": score
        })

    best_offer = max(offers, key=lambda x: x["score"])

    return best_offer


def rank_all_products():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT product FROM offers")

    rows = cursor.fetchall()

    conn.close()

    products = set(normalize_product(row[0]) for row in rows)

    results = {}

    for product in products:

        best_offer = rank_offers(product)

        if best_offer:
            results[product] = best_offer

    return results