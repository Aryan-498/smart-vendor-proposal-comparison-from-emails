import json
import time

from ai.gemini_client import get_client
from utils.logger import log

MODEL       = "gemini-2.5-flash"
MAX_RETRIES = 5


def clean_json(text):
    text = text.strip()
    text = text.replace("```json", "").replace("```", "")
    return text.strip()


def _call_gemini(client, prompt: str) -> str:
    """Call Gemini with exponential backoff on rate limit errors."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )
            return response.text

        except Exception as e:
            err = str(e)

            if "429" in err or "quota" in err.lower() or "rate" in err.lower() or "RESOURCE_EXHAUSTED" in err:
                wait = 60 * attempt
                log(f"Gemini rate limit (attempt {attempt}/{MAX_RETRIES}) — waiting {wait}s...")
                time.sleep(wait)
                continue

            if "expired" in err.lower() or "API_KEY_INVALID" in err or "INVALID_ARGUMENT" in err:
                raise RuntimeError(
                    f"Gemini API key error: {err}\n"
                    "Go to https://aistudio.google.com → Get API Key → Create new key\n"
                    "Then update GEMINI_API_KEY in your .env and Streamlit secrets."
                )

            raise

    raise RuntimeError(
        f"Gemini rate limit persisted after {MAX_RETRIES} retries.\n"
        "Your daily quota may be exhausted. Try again tomorrow\n"
        "or use a different API key."
    )


def extract_offers_batch(emails: list[dict]) -> list[dict]:
    """
    Send ALL non-spam emails in a single Gemini request.
    Retries up to 5 times with increasing wait on rate limit.
    """

    if not emails:
        return []

    client = get_client()

    email_blocks = ""
    for i, email in enumerate(emails, start=1):
        email_blocks += f"""
--- EMAIL {i} ---
From : {email.get('sender', '')}
Body :
{email.get('body', '').strip()[:3000]}
"""

    prompt = f"""
You are an AI system that extracts structured vendor/buyer offers from business emails.

Below are {len(emails)} emails. For each email that contains a product offer, extract the details.
If an email has NO product offer (notification, receipt, unrelated), return nothing for it.

Rules:
- Extract ALL product offers across all emails.
- One email can have multiple products — one entry per product.
- Convert quantities to numbers. If unit missing, assume kg.
- If price written like "45/kg", return 45.
- Detect vendor name from signature if possible.
- Detect intent: order, offer, negotiation, inquiry, or unknown.
- Include the email number as "email_index".

Return ONLY a valid JSON array — no markdown, no explanation.
If no offers found in any email, return [].

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
        log(f"Sending {len(emails)} emails to Gemini (model: {MODEL})...")

        text   = _call_gemini(client, prompt)
        offers = json.loads(clean_json(text))

        if isinstance(offers, dict):
            offers = [offers]

        # Attach sender info back to each offer
        for offer in offers:
            idx = offer.get("email_index", 1) - 1
            if 0 <= idx < len(emails):
                if not offer.get("vendor"):
                    offer["vendor"] = emails[idx].get("sender", "").split("<")[0].strip()
                offer["vendor_email"] = emails[idx].get("sender_email", "")
            offer.pop("email_index", None)

        log(f"Gemini extracted {len(offers)} offers from {len(emails)} emails.")
        return offers

    except json.JSONDecodeError as e:
        log(f"Gemini returned invalid JSON: {e}")
        return []

    except RuntimeError as e:
        log(str(e))
        return []

    except Exception as e:
        log(f"Gemini batch extraction failed: {e}")
        return []


def extract_offer(email_text: str) -> list[dict]:
    """Single-email wrapper for backwards compatibility with main.py CLI."""
    if not email_text or not email_text.strip():
        return []
    return extract_offers_batch([{"sender": "", "body": email_text}])
