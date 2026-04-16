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


def normalize_unit(unit, quantity=None):
    """
    BUG FIX: previously converted 'ton' to 'kg' without adjusting quantity.
    Now returns both the normalized unit AND the correctly scaled quantity.
    e.g. 5 tons → 5000 kg
    """

    if not unit:
        return "kg", quantity

    unit = unit.lower().strip()

    if unit in ["kilogram", "kilograms"]:
        return "kg", quantity

    if unit in ["ton", "tons", "tonne", "tonnes", "mt"]:
        # BUG FIX: multiply quantity by 1000 when converting ton → kg
        converted_quantity = (quantity * 1000) if quantity is not None else quantity
        return "kg", converted_quantity

    if unit in ["gram", "grams", "g"]:
        converted_quantity = (quantity / 1000) if quantity is not None else quantity
        return "kg", converted_quantity

    if unit in ["quintal", "quintals"]:
        converted_quantity = (quantity * 100) if quantity is not None else quantity
        return "kg", converted_quantity

    return unit, quantity


def normalize_vendor(vendor):

    if not vendor:
        return "unknown"

    return vendor.strip()


def normalize_offer(offer):

    offer["product"] = normalize_product(offer.get("product"))

    # BUG FIX: pass quantity so it gets correctly scaled during unit conversion
    raw_quantity = offer.get("quantity")
    normalized_unit, normalized_quantity = normalize_unit(
        offer.get("unit"), raw_quantity
    )

    offer["unit"] = normalized_unit
    offer["quantity"] = normalized_quantity
    offer["vendor"] = normalize_vendor(offer.get("vendor"))

    return offer