def normalize_product(product):

    if not product:
        return ""

    product = product.lower().strip()

    aliases = {
        "basmati rice": "rice",
        "rice grain": "rice",
        "wheat grain": "wheat",
        "maize": "corn"
    }

    return aliases.get(product, product)


def normalize_unit(unit):

    if not unit:
        return "kg"

    unit = unit.lower()

    if unit in ["kilogram", "kilograms"]:
        return "kg"

    if unit in ["ton", "tons"]:
        return "kg"

    return unit


def normalize_vendor(vendor):

    if not vendor:
        return "unknown"

    return vendor.strip()


def normalize_offer(offer):

    offer["product"] = normalize_product(offer.get("product"))
    offer["unit"] = normalize_unit(offer.get("unit"))
    offer["vendor"] = normalize_vendor(offer.get("vendor"))

    return offer