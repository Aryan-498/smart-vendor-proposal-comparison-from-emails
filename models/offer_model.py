from dataclasses import dataclass, field


@dataclass
class Offer:
    """
    IMPROVEMENT: converted to dataclass for type safety and cleaner construction.
    Previously defined as a plain class with manual __init__ and was never used.
    """
    product: str
    price: float
    quantity: float
    vendor: str
    intent: str
    unit: str = "kg"
    profit: float = 0.0
    score: float = 0.0

    def to_dict(self):
        return {
            "product": self.product,
            "price": self.price,
            "quantity": self.quantity,
            "vendor": self.vendor,
            "intent": self.intent,
            "unit": self.unit,
            "profit": self.profit,
            "score": self.score
        }