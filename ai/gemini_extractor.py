import json
from ai.gemini_client import get_client
from utils.logger import log


def clean_json(text):
    """Remove markdown formatting if Gemini wraps JSON in ```json blocks."""

    text = text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")

    return text.strip()


def extract_offer(email_text):
    """
    Extracts vendor offers from an email using Gemini.
    Returns a list of offer dicts.
    """

    if not email_text or not email_text.strip():
        log("Empty email body — skipping extraction.")
        return []

    client = get_client()

    prompt = f"""
You are an AI system that extracts structured vendor offers from business emails.

Your task:
Identify product offers inside the email and return structured JSON.

Rules:
- Extract ALL product offers mentioned.
- If multiple products appear, return multiple entries.
- Convert quantities to numbers.
- If unit is missing assume kg.
- If price is written like "45/kg", return 45.
- Detect vendor name from signature if possible.
- Detect intent: order, negotiation, inquiry, or unknown.

Return ONLY a valid JSON array in this exact format (no markdown, no explanation):

[
 {{
   "product": "",
   "quantity": 0,
   "unit": "",
   "price": 0,
   "vendor": "",
   "intent": ""
 }}
]

Email:
{email_text}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = clean_json(response.text)

        offers = json.loads(text)

        # Ensure output is always a list
        if isinstance(offers, dict):
            offers = [offers]

        return offers

    except json.JSONDecodeError as e:
        log(f"Gemini returned invalid JSON: {e}")
        return []

    except Exception as e:
        log(f"Gemini extraction failed: {e}")
        return []