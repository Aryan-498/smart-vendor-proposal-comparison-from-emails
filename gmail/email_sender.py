import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from gmail.gmail_auth import authenticate_gmail
from utils.logger import log


def build_service():
    creds = authenticate_gmail()
    return build("gmail", "v1", credentials=creds)


def _create_message(to, subject, body_text):
    msg = MIMEText(body_text)
    msg["to"]      = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_stock_exceeded_reply(vendor_email, vendor_name, product, requested_qty, available_stock):
    subject = f"Re: Your offer for {product.title()} — Stock Availability Update"
    body = f"""Dear {vendor_name},

Thank you for your offer regarding {product.title()}.

We regret to inform you that we are currently unable to fulfil the requested
quantity of {requested_qty} kg for {product.title()}.

Our current available stock is {available_stock} kg, which is below your request.

We would be happy to discuss a partial fulfilment or revisit once stock is replenished.

Best regards,
Procurement Team
"""
    try:
        service = build_service()
        service.users().messages().send(
            userId="me", body=_create_message(vendor_email, subject, body)
        ).execute()
        log(f"Stock-exceeded reply sent to {vendor_email}")
    except Exception as e:
        log(f"Failed to send stock-exceeded reply: {e}")


def send_counter_offer(vendor_email, vendor_name, product, original_price,
                       counter_price, quantity, note=""):
    """Admin sends a counter-offer price to a vendor."""
    subject = f"Counter Offer — {product.title()}"
    body = f"""Dear {vendor_name},

Thank you for your offer for {product.title()}.

We would like to propose the following counter offer:

  Product  : {product.title()}
  Quantity : {quantity} kg
  Our Price: ₹{counter_price}/kg  (your offer: ₹{original_price}/kg)

{('Additional note: ' + note) if note else ''}

Please let us know if you would like to proceed on these terms.

Best regards,
Procurement Team
"""
    try:
        service = build_service()
        service.users().messages().send(
            userId="me", body=_create_message(vendor_email, subject, body)
        ).execute()
        log(f"Counter offer sent to {vendor_email}")
        return True
    except Exception as e:
        log(f"Failed to send counter offer: {e}")
        return False


def send_rejection(vendor_email, vendor_name, product, reason=""):
    """Admin rejects a vendor offer."""
    subject = f"Re: Your Offer for {product.title()} — Update"
    body = f"""Dear {vendor_name},

Thank you for your offer for {product.title()}.

After careful consideration, we regret that we are unable to accept your
offer at this time.

{('Reason: ' + reason) if reason else ''}

We appreciate your interest and hope to work with you in the future.

Best regards,
Procurement Team
"""
    try:
        service = build_service()
        service.users().messages().send(
            userId="me", body=_create_message(vendor_email, subject, body)
        ).execute()
        log(f"Rejection sent to {vendor_email}")
        return True
    except Exception as e:
        log(f"Failed to send rejection: {e}")
        return False


def send_inventory_update_confirmation(admin_email, updates):
    subject = "Inventory Update Confirmation"
    lines = "\n".join(
        f"  • {p.title()}: stock={d.get('stock','unchanged')}, cost_price={d.get('cost_price','unchanged')}"
        for p, d in updates.items()
    )
    body = f"Hello,\n\nInventory updated:\n\n{lines}\n\nBest regards,\nSmart Vendor System\n"
    try:
        service = build_service()
        service.users().messages().send(
            userId="me", body=_create_message(admin_email, subject, body)
        ).execute()
    except Exception as e:
        log(f"Failed to send confirmation: {e}")