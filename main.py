from gmail.email_reader import fetch_emails
from ai.gemini_extractor import extract_offer
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

AUTOMATED_KEYWORDS = [
    "no-reply",
    "noreply",
    "notification",
    "newsletter",
    "updates"
]

SOCIAL_DOMAINS = [
    "instagram",
    "facebook",
    "linkedin",
    "twitter",
    "x.com",
    "reddit",
    "discord",
    "youtube",
    "tiktok",
    "chess.com",
    "github.com"
]


def is_automated_email(sender):

    sender_lower = sender.lower()

    for keyword in AUTOMATED_KEYWORDS:
        if keyword in sender_lower:
            return True

    for domain in SOCIAL_DOMAINS:
        if domain in sender_lower:
            return True

    return False


def extract_email_address(sender: str) -> str:
    """
    Parse the raw email address from a sender string.
    e.g. 'John Doe <john@example.com>' → 'john@example.com'
    e.g. 'john@example.com' → 'john@example.com'
    """
    if "<" in sender and ">" in sender:
        return sender.split("<")[1].split(">")[0].strip().lower()
    return sender.strip().lower()


def is_admin_email(sender: str) -> bool:
    return extract_email_address(sender) == ADMIN_EMAIL.lower()


def main():

    # Ensure all DB tables exist before anything runs
    create_tables()

    log("Fetching emails...")
    emails = fetch_emails("2024/01/01", "2026/12/31")
    log(f"Total emails fetched: {len(emails)}")

    for email in emails:

        sender  = email["sender"]
        subject = email.get("subject", "")
        body    = email["body"]

        # ── Feature 2: Admin inventory update ────────────────────────────────
        if is_admin_email(sender):
            if ADMIN_UPDATE_SUBJECT_KEYWORD.lower() in subject.lower():
                handle_admin_inventory_email(
                    extract_email_address(sender),
                    subject,
                    body
                )
                continue  # don't process admin emails as vendor offers
            else:
                log(f"Email from admin ({sender}) — subject doesn't match update keyword, skipping.")
                continue

        # ── Spam / automated filter ───────────────────────────────────────────
        if is_automated_email(sender):
            log(f"Skipping automated email from: {sender}")
            continue

        log(f"Processing email from: {sender}")

        offers = extract_offer(body)

        if not offers:
            log("No offers found in email.")
            continue

        for offer in offers:

            # Fallback vendor name from sender
            if not offer.get("vendor"):
                offer["vendor"] = sender.split("<")[0].strip()

            offer = normalize_offer(offer)

            product   = offer.get("product")
            quantity  = offer.get("quantity") or 0
            available = get_available_stock(product)

            # ── Feature 1: Auto-reply when order exceeds stock ────────────────
            if quantity > available:
                log(
                    f"Order exceeds stock — product='{product}', "
                    f"requested={quantity}, available={available}"
                )

                if AUTO_REPLY_ON_STOCK_EXCEEDED:
                    vendor_email = extract_email_address(sender)
                    vendor_name  = sender.split("<")[0].strip() or vendor_email
                    send_stock_exceeded_reply(
                        vendor_email,
                        vendor_name,
                        product,
                        quantity,
                        available
                    )

                # Do NOT save this offer — it can't be fulfilled
                continue

            # Normal path — save valid offer
            try:
                save_offer(offer)
                log(f"Saved offer: {offer}")
            except Exception as e:
                log(f"Failed to save offer: {e}")

        print("-" * 50)


if __name__ == "__main__":
    main()