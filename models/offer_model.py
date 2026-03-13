class Offer:

    def __init__(self, product, price, quantity, vendor, intent):
        self.product = product
        self.price = price
        self.quantity = quantity
        self.vendor = vendor
        self.intent = intent
        self.profit = 0
        self.score = 0