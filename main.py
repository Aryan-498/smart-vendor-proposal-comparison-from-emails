from gmail.email_reader import fetch_emails
from ai.gemini_extractor import extract_offer
from database.offer_history import save_offer
from processing.normalization import normalize_offer

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

    print("Fetching emails...")

    emails = fetch_emails("2024/01/01", "2026/12/31")

    print(f"Total emails fetched: {len(emails)}\n")

    for email in emails:

        sender = email["sender"]
        body = email["body"]

        # filter spam / automated emails
        if is_automated_email(sender):
           print(f"Skipping automated email from: {sender}")
           continue

        print(f"Processing email from: {sender}")

        offers = extract_offer(body)

        if not offers:
            continue

        for offer in offers:

            # fallback vendor
            if not offer.get("vendor"):
                offer["vendor"] = sender.split("<")[0].strip()

            offer = normalize_offer(offer)

            save_offer(offer)

            print("Extracted offer:", offer)

        print("-" * 50)


if __name__ == "__main__":
    main()