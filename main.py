from gmail.email_reader import fetch_emails
from ai.gemini_extractor import extract_offers_batch
from database.offer_history import save_offer
from database.db_manager import create_tables
from processing.normalization import normalize_offer
from inventory.inventory_manager import get_available_stock
from inventory.inventory_updater import handle_admin_inventory_email
from gmail.email_sender import send_stock_exceeded_reply
from utils.logger import log
from config.settings import (
    AUTO_REPLY_ON_STOCK_EXCEEDED,
    ADMIN_EMAIL,
    ADMIN_UPDATE_SUBJECT_KEYWORD
)

AUTOMATED_KEYWORDS = ["no-reply", "noreply", "notification", "newsletter", "updates"]
SOCIAL_DOMAINS     = ["instagram", "facebook", "linkedin", "twitter", "x.com",
                      "reddit", "discord", "youtube", "tiktok", "chess.com", "github.com"]
JUNK_VENDORS       = ["chess.com", "github", "instagram", "facebook",
                      "twitter", "linkedin", "discord", "youtube", "tiktok"]


def is_automated_email(sender):
    s = sender.lower()
    return any(k in s for k in AUTOMATED_KEYWORDS) or any(d in s for d in SOCIAL_DOMAINS)


def extract_email_address(sender: str) -> str:
    if "<" in sender and ">" in sender:
        return sender.split("<")[1].split(">")[0].strip().lower()
    return sender.strip().lower()


def is_admin_email(sender: str) -> bool:
    return extract_email_address(sender) == ADMIN_EMAIL.lower()


def main():
    create_tables()

    log("Fetching emails...")
    all_emails = fetch_emails("2024/01/01", "2026/12/31")
    log(f"Total emails fetched: {len(all_emails)}")

    # ── Step 1: separate admin emails and valid vendor emails ─────────────────
    valid_emails = []

    for email in all_emails:
        sender  = email["sender"]
        subject = email.get("subject", "")
        body    = email["body"]

        if is_admin_email(sender):
            if ADMIN_UPDATE_SUBJECT_KEYWORD.lower() in subject.lower():
                handle_admin_inventory_email(extract_email_address(sender), subject, body)
            else:
                log(f"Admin email skipped (subject mismatch): {subject}")
            continue

        if is_automated_email(sender):
            log(f"Skipping automated email from: {sender}")
            continue

        email["sender_email"] = extract_email_address(sender)
        valid_emails.append(email)

    log(f"Valid vendor emails to process: {len(valid_emails)}")

    if not valid_emails:
        log("No valid emails to send to Gemini.")
        return

    # ── Step 2: ONE Gemini call for ALL valid emails ──────────────────────────
    offers = extract_offers_batch(valid_emails)

    log(f"Total offers extracted: {len(offers)}")

    # ── Step 3: validate and save each offer ──────────────────────────────────
    for offer in offers:
        offer = normalize_offer(offer)

        vendor_l = offer.get("vendor", "").lower()
        if any(j in vendor_l for j in JUNK_VENDORS):
            log(f"Skipping junk vendor: {offer.get('vendor')}")
            continue

        product  = offer.get("product")
        quantity = offer.get("quantity") or 0
        available = get_available_stock(product)

        if quantity > available:
            log(f"Order exceeds stock — product='{product}', requested={quantity}, available={available}")
            if AUTO_REPLY_ON_STOCK_EXCEEDED:
                ve = offer.get("vendor_email", "")
                vn = offer.get("vendor", ve)
                if ve:
                    send_stock_exceeded_reply(ve, vn, product, quantity, available)
            continue

        try:
            save_offer(offer)
            log(f"Saved offer: {offer}")
        except Exception as e:
            log(f"Failed to save offer: {e}")

    print("-" * 50)
    log("Pipeline complete.")


if __name__ == "__main__":
    main()