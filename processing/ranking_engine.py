import math

from database.db_manager import get_connection
from processing.normalization import normalize_product
from processing.intent_filter import intent_score
from processing.profit_calculator import calculate_profit, profit_score
from inventory.inventory_manager import get_available_stock


def get_vendor_score(vendor):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT total_orders FROM vendors WHERE name = ?", (vendor,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return 0

    total_orders = row[0]

    return math.log(1 + total_orders)


def rank_offers(product):

    product = normalize_product(product)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT product, quantity, unit, price, vendor, intent FROM offers"
    )

    rows = cursor.fetchall()

    conn.close()

    product_rows = []

    for row in rows:

        p, quantity, unit, price, vendor, intent = row

        if normalize_product(p) == product:
            product_rows.append(row)

    if not product_rows:
        return None

    # inventory filter
    available_stock = get_available_stock(product)

    valid_rows = []

    for row in product_rows:

        p, quantity, unit, price, vendor, intent = row

        if quantity <= available_stock:
            valid_rows.append(row)

    if not valid_rows:
        return None

    profits = []

    for row in valid_rows:

        p, quantity, unit, price, vendor, intent = row

        profit = calculate_profit(product, price)

        profits.append(profit)

    max_profit = max(profits) if profits else 1
    max_quantity = max(row[1] for row in valid_rows)

    offers = []

    for row in valid_rows:

        product, quantity, unit, price, vendor, intent = row

        profit = calculate_profit(product, price)

        p_score = profit_score(profit, max_profit)

        quantity_score = quantity / max_quantity if max_quantity else 0

        vendor_score = get_vendor_score(vendor)

        intent_sc = intent_score(intent)

        score = (
            0.4 * p_score +
            0.3 * quantity_score +
            0.2 * vendor_score +
            0.1 * intent_sc
        )

        offers.append({
            "vendor": vendor,
            "product": product,
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

    products = set()

    for row in rows:
        products.add(normalize_product(row[0]))

    results = {}

    for product in products:

        best_offer = rank_offers(product)

        if best_offer:
            results[product] = best_offer

    return results