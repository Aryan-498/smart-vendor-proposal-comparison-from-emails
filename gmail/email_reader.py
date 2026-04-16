import base64
from googleapiclient.discovery import build
from gmail.gmail_auth import authenticate_gmail
from database.db_manager import get_connection
from utils.logger import log


def is_already_processed(email_id):
    """Check if this email has already been processed to avoid duplicates."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM processed_emails WHERE email_id = ?", (email_id,))
    row = cursor.fetchone()

    conn.close()

    return row is not None


def mark_as_processed(email_id):
    """Mark an email as processed so it won't be re-processed on next run."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO processed_emails (email_id) VALUES (?)",
        (email_id,)
    )

    conn.commit()
    conn.close()


def decode_body(data):
    """
    BUG FIX: Gmail API returns body as base64url-encoded string.
    This decodes it to plain text so Gemini can read it.
    """
    if not data:
        return ""

    try:
        decoded_bytes = base64.urlsafe_b64decode(data + "==")
        return decoded_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        log(f"Failed to decode email body: {e}")
        return ""


def fetch_emails(start_date, end_date):

    creds = authenticate_gmail()
    service = build("gmail", "v1", credentials=creds)

    # BUG FIX: query was built but never passed — added q=query
    query = f"in:inbox after:{start_date} before:{end_date}"

    emails = []
    page_token = None

    # IMPROVEMENT: paginate through all results instead of stopping at 10
    while True:

        params = {
            "userId": "me",
            "maxResults": 50,
            "q": query  # BUG FIX: was missing entirely before
        }

        if page_token:
            params["pageToken"] = page_token

        results = service.users().messages().list(**params).execute()

        messages = results.get("messages", [])

        for message in messages:

            email_id = message["id"]

            # IMPROVEMENT: skip already-processed emails
            if is_already_processed(email_id):
                log(f"Skipping already processed email: {email_id}")
                continue

            msg = service.users().messages().get(
                userId="me",
                id=email_id,
                format="full"
            ).execute()

            payload = msg["payload"]
            headers = payload.get("headers", [])

            subject = ""
            sender = ""

            for header in headers:
                if header["name"] == "Subject":
                    subject = header["value"]
                if header["name"] == "From":
                    sender = header["value"]

            body = ""

            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        raw = part["body"].get("data", "")
                        body = decode_body(raw)  # BUG FIX: decode base64
                        break
            else:
                raw = payload["body"].get("data", "")
                body = decode_body(raw)  # BUG FIX: decode base64

            emails.append({
                "id": email_id,
                "subject": subject,
                "sender": sender,
                "body": body
            })

            mark_as_processed(email_id)

        page_token = results.get("nextPageToken")

        if not page_token:
            break

    return emails