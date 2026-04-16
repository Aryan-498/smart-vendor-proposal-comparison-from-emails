from gmail.email_reader import fetch_emails
from ai.gemini_extractor import extract_offer
from database.offer_history import save_offer
from database.db_manager import create_tables
from processing.normalization import normalize_offer
from utils.logger import log

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


def main():

    # BUG FIX: ensure tables exist before any DB operations
    create_tables()

    log("Fetching emails...")

    emails = fetch_emails("2026/03/07", "2026/04/30")

    log(f"Total emails fetched: {len(emails)}")

    for email in emails:

        sender = email["sender"]
        body = email["body"]

        # filter spam / automated emails
        if is_automated_email(sender):
            log(f"Skipping automated email from: {sender}")
            continue

        log(f"Processing email from: {sender}")

        offers = extract_offer(body)

        if not offers:
            log("No offers found in email.")
            continue

        for offer in offers:

            # fallback vendor
            if not offer.get("vendor"):
                offer["vendor"] = sender.split("<")[0].strip()

            offer = normalize_offer(offer)

            try:
                save_offer(offer)
                log(f"Saved offer: {offer}")
            except Exception as e:
                log(f"Failed to save offer: {e}")

        print("-" * 50)


if __name__ == "__main__":
    main()