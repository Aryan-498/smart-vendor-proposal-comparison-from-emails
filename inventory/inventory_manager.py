inventory_data = {
    "rice": {
        "stock": 1000,
        "cost_price": 40
    },
    "wheat": {
        "stock": 800,
        "cost_price": 35
    },
    "corn": {
        "stock": 500,
        "cost_price": 25
    }
}


def get_available_stock(product):

    product = product.lower()

    if product not in inventory_data:
        return 0

    return inventory_data[product]["stock"]


def get_cost_price(product):

    product = product.lower()

    if product not in inventory_data:
        return 0

    return inventory_data[product]["cost_price"]