import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ─── Gmail OAuth Scopes ───────────────────────────────────────────────────────
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# ─── Google OAuth (for website login) ────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")

# ─── Paths ────────────────────────────────────────────────────────────────────
DATABASE_PATH  = "data/vendor_history.db"
INVENTORY_PATH = "data/inventory.json"

# ─── Ranking Weights ──────────────────────────────────────────────────────────
PROFIT_WEIGHT   = 0.4
QUANTITY_WEIGHT = 0.3
VENDOR_WEIGHT   = 0.2
INTENT_WEIGHT   = 0.1

# ─── Feature 1: Auto-reply when order exceeds inventory ───────────────────────
AUTO_REPLY_ON_STOCK_EXCEEDED = True

# ─── Feature 2: Admin email ───────────────────────────────────────────────────
ADMIN_EMAIL                  = os.getenv("ADMIN_EMAIL", "aryanranja771@gmail.com")
ADMIN_UPDATE_SUBJECT_KEYWORD = "update inventory"