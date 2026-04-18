import json
from ai.gemini_client import get_client
from utils.logger import log


def clean_json(text):
    text = text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")
    return text.strip()


def extract_offers_batch(emails: list[dict]) -> list[dict]:
    """
    Send ALL non-spam emails in a single Gemini request.

    Each email in the list should be:
        { "id": "...", "sender": "...", "body": "..." }

    Returns a flat list of offers, each with an extra "email_id" field
    so we know which email each offer came from.
    """

    if not emails:
        return []

    client = get_client()

    # Build one big prompt with all emails numbered
    email_blocks = ""
    for i, email in enumerate(emails, start=1):
        email_blocks += f"""
--- EMAIL {i} ---
From   : {email.get('sender', '')}
Body   :
{email.get('body', '').strip()}
"""

    prompt = f"""
You are an AI system that extracts structured vendor/buyer offers from business emails.

Below are {len(emails)} emails. For each email that contains a product offer, extract the offer details.
If an email has NO product offer (e.g. it's a notification, receipt, or unrelated message), skip it entirely.

Rules:
- Extract ALL product offers mentioned across all emails.
- One email can have multiple products — return one entry per product.
- Convert quantities to numbers.
- If unit is missing, assume kg.
- If price is written like "45/kg", return 45.
- Detect vendor name from the email signature if possible.
- Detect intent: order, offer, negotiation, inquiry, or unknown.
- Include the email number (1, 2, 3 ...) as "email_index" in each result.

Return ONLY a valid JSON array — no markdown, no explanation, nothing else.
If no emails contain offers, return [].

Format:
[
  {{
    "email_index": 1,
    "product": "",
    "quantity": 0,
    "unit": "",
    "price": 0,
    "vendor": "",
    "intent": ""
  }}
]

{email_blocks}
"""

    try:
        log(f"Sending {len(emails)} emails to Gemini in a single batch request...")

        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )

        text   = clean_json(response.text)
        offers = json.loads(text)

        if isinstance(offers, dict):
            offers = [offers]

        # Attach the original sender to each offer as fallback vendor
        for offer in offers:
            idx = offer.get("email_index", 1) - 1
            if 0 <= idx < len(emails):
                if not offer.get("vendor"):
                    sender = emails[idx].get("sender", "")
                    offer["vendor"] = sender.split("<")[0].strip()
                offer["vendor_email"] = emails[idx].get("sender_email", "")
            offer.pop("email_index", None)  # clean up before saving

        log(f"Gemini extracted {len(offers)} offers from {len(emails)} emails.")
        return offers

    except json.JSONDecodeError as e:
        log(f"Gemini returned invalid JSON: {e}")
        return []

    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            log("Gemini rate limit hit — try again in a minute.")
        else:
            log(f"Gemini batch extraction failed: {e}")
        return []


def extract_offer(email_text: str) -> list[dict]:
    """
    Single-email fallback used by main.py CLI pipeline.
    Wraps the batch function for backwards compatibility.
    """
    if not email_text or not email_text.strip():
        return []

    results = extract_offers_batch([{"sender": "", "body": email_text}])
    return results