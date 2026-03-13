from googleapiclient.discovery import build
from gmail.gmail_auth import authenticate_gmail

def fetch_emails(start_date, end_date):

    creds = authenticate_gmail()
    service = build("gmail", "v1", credentials=creds)

    query = f"in:inbox after:{start_date} before:{end_date}"

    results = service.users().messages().list(
    userId="me",
    maxResults=10
).execute()

    messages = results.get("messages", [])

    emails = []

    for message in messages:
        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full"
        ).execute()

        payload = msg["payload"]
        headers = payload.get("headers")

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
                    body = part["body"].get("data", "")
        else:
            body = payload["body"].get("data", "")

        emails.append({
            "id": message["id"],
            "subject": subject,
            "sender": sender,
            "body": body
        })

    return emails