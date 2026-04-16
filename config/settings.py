import os
from dotenv import load_dotenv

load_dotenv()

# API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gmail scopes
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Database path
DATABASE_PATH = "data/vendor_history.db"

# Inventory file — IMPROVEMENT: used by inventory_manager to load dynamically
INVENTORY_PATH = "data/inventory.json"

# Ranking weights
PROFIT_WEIGHT = 0.4
QUANTITY_WEIGHT = 0.3
VENDOR_WEIGHT = 0.2
INTENT_WEIGHT = 0.1