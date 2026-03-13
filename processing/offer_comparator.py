from processing.ranking_engine import rank_all_products


def get_best_offers():

    results = rank_all_products()

    best_offers = []

    for product, offer in results.items():

        best_offers.append({
            "product": product,
            "vendor": offer["vendor"],
            "price": offer["price"],
            "quantity": offer["quantity"],
            "score": round(offer["score"], 3)
        })

    return best_offers


def print_best_offers():

    best_offers = get_best_offers()

    if not best_offers:
        print("No valid offers found.")
        return

    print("\nBEST OFFERS\n")

    for offer in best_offers:

        print("Product:", offer["product"].upper())
        print("Vendor:", offer["vendor"])
        print("Price:", offer["price"])
        print("Quantity:", offer["quantity"])
        print("Score:", offer["score"])

        print("-" * 40)