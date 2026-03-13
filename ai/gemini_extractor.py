import json
from ai.gemini_client import get_client


def clean_json(text):
    """
    Removes markdown formatting if Gemini returns JSON wrapped in ```json
    """
    text = text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")
    return text


def extract_offer(email_text):
    """
    Extracts vendor offers from an email using Gemini.
    Returns a list of offers.
    """

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

Return ONLY JSON in this format:

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

    except Exception as e:

        print("Gemini extraction failed:", e)
        return []