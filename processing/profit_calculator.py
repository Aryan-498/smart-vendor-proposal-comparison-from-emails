from inventory.inventory_manager import get_cost_price


def calculate_profit(product, price):

    product = product.lower().strip()
    cost = get_cost_price(product)
    profit = price - cost

    return profit


def profit_score(profit, max_profit):

    if max_profit <= 0:
        return 0

    return profit / max_profit