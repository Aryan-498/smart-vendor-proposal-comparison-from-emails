import os
from dotenv import load_dotenv

load_dotenv()

# API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gmail scopes — send scope added so we can reply when stock is exceeded
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

# Database path
DATABASE_PATH = "data/vendor_history.db"

# Inventory file
INVENTORY_PATH = "data/inventory.json"

# Ranking weights
PROFIT_WEIGHT = 0.4
QUANTITY_WEIGHT = 0.3
VENDOR_WEIGHT = 0.2
INTENT_WEIGHT = 0.1

# ─── Feature 1: Auto-reply when order exceeds inventory ───────────────────────
# Set to False to disable the auto-reply feature entirely
AUTO_REPLY_ON_STOCK_EXCEEDED = True

# ─── Feature 2: Trusted admin email that can update inventory via email ────────
# Only emails from this address will be allowed to update stock / cost_price
ADMIN_EMAIL = "aryanranja771@gmail.com"

# Subject line the admin email must contain (case-insensitive)
ADMIN_UPDATE_SUBJECT_KEYWORD = "update inventory"