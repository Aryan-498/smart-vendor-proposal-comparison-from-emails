import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from gmail.gmail_auth import authenticate_gmail
from utils.logger import log


def build_service():
    creds = authenticate_gmail()
    return build("gmail", "v1", credentials=creds)


def _create_message(to, subject, body_text):
    """Encode a plain-text email into the base64 format Gmail API expects."""

    msg = MIMEText(body_text)
    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_stock_exceeded_reply(vendor_email, vendor_name, product, requested_qty, available_stock):
    """
    Feature 1 — Auto-reply when an order exceeds available inventory.
    Sends a polite email to the vendor explaining the shortfall.
    """

    subject = f"Re: Your offer for {product.title()} — Stock Availability Update"

    body = f"""Dear {vendor_name},

Thank you for your offer regarding {product.title()}.

We appreciate your interest, however, we regret to inform you that we are currently
unable to fulfil the requested quantity of {requested_qty} kg for {product.title()}.

Our current available stock for {product.title()} is {available_stock} kg,
which is below your requested quantity.

We would be happy to discuss a partial fulfilment or revisit your offer once
our stock is replenished.

Please feel free to reach out if you have any questions.

Best regards,
Procurement Team
"""

    try:
        service = build_service()
        message = _create_message(vendor_email, subject, body)
        service.users().messages().send(userId="me", body=message).execute()
        log(f"Stock-exceeded reply sent to {vendor_email} for product '{product}'")

    except Exception as e:
        log(f"Failed to send stock-exceeded reply to {vendor_email}: {e}")


def send_inventory_update_confirmation(admin_email, updates):
    """
    Feature 2 — Confirmation email sent back to admin after inventory update.
    """

    subject = "Inventory Update Confirmation"

    lines = "\n".join(
        f"  • {product.title()}: stock={data.get('stock', 'unchanged')}, "
        f"cost_price={data.get('cost_price', 'unchanged')}"
        for product, data in updates.items()
    )

    body = f"""Hello,

The following inventory updates have been applied successfully:

{lines}

These changes are now live.

Best regards,
Smart Vendor System
"""

    try:
        service = build_service()
        message = _create_message(admin_email, subject, body)
        service.users().messages().send(userId="me", body=message).execute()
        log(f"Inventory update confirmation sent to {admin_email}")

    except Exception as e:
        log(f"Failed to send confirmation to {admin_email}: {e}")