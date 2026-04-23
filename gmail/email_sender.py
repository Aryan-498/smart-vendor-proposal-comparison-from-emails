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


def _send(to, subject, body):
    """Internal helper — builds service and sends. Returns True/False."""
    try:
        service = build_service()
        service.users().messages().send(
            userId="me", body=_create_message(to, subject, body)
        ).execute()
        log(f"Email sent to {to} | {subject}")
        return True
    except Exception as e:
        log(f"Failed to send email to {to}: {e}")
        return False


# ── Existing functions ────────────────────────────────────────────────────────

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
    _send(vendor_email, subject, body)


def send_counter_offer(vendor_email, vendor_name, product, original_price,
                       counter_price, quantity, note=""):
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
    return _send(vendor_email, subject, body)


def send_rejection(vendor_email, vendor_name, product, reason=""):
    subject = f"Re: Your Offer for {product.title()} — Update"
    body = f"""Dear {vendor_name},

Thank you for your offer for {product.title()}.

After careful consideration, we regret that we are unable to accept your offer at this time.

{('Reason: ' + reason) if reason else ''}

We appreciate your interest and hope to work with you in the future.

Best regards,
Procurement Team
"""
    return _send(vendor_email, subject, body)


def send_inventory_update_confirmation(admin_email, updates):
    subject = "Inventory Update Confirmation"
    lines = "\n".join(
        f"  • {p.title()}: stock={d.get('stock','unchanged')}, "
        f"cost_price={d.get('cost_price','unchanged')}"
        for p, d in updates.items()
    )
    body = f"Hello,\n\nInventory updated:\n\n{lines}\n\nBest regards,\nSmart Vendor System\n"
    _send(admin_email, subject, body)


# ── Feature: Accept offer notification ───────────────────────────────────────

def send_acceptance(vendor_email, vendor_name, product, quantity, price):
    """
    Notify vendor their offer has been accepted.
    Sent when admin clicks Accept in the dashboard.
    """
    subject = f"✅ Your Offer for {product.title()} has been Accepted!"
    body = f"""Dear {vendor_name},

Great news! We are pleased to inform you that your offer has been accepted.

  Product  : {product.title()}
  Quantity : {quantity} kg
  Price    : ₹{price}/kg
  Total    : ₹{quantity * price:,.0f}

Our team will be in touch shortly to discuss delivery and payment details.

Thank you for doing business with us.

Best regards,
Procurement Team
"""
    return _send(vendor_email, subject, body)


# ── Feature: User status notification (web offers) ───────────────────────────

def notify_user_status(user_email, user_name, product, quantity, price, status,
                       counter_price=None, reason=None):
    """
    Email notification sent to users who submitted offers via the website
    when admin changes the offer status (accepted / rejected / counter).
    """

    if status == "accepted":
        subject = f"✅ Your offer for {product.title()} was accepted!"
        body = f"""Dear {user_name},

We're happy to inform you that your offer has been accepted!

  Product  : {product.title()}
  Quantity : {quantity} kg
  Price    : ₹{price}/kg
  Total    : ₹{quantity * price:,.0f}

Our procurement team will contact you soon to arrange next steps.

Thank you!
Procurement Team
"""

    elif status == "rejected":
        subject = f"Update on your offer for {product.title()}"
        body = f"""Dear {user_name},

Thank you for submitting an offer for {product.title()}.

After review, we are unable to proceed with your offer at this time.

{('Reason: ' + reason) if reason else ''}

We hope to work with you in the future.

Best regards,
Procurement Team
"""

    elif status == "counter":
        subject = f"Counter Offer for {product.title()}"
        body = f"""Dear {user_name},

Thank you for your offer for {product.title()}.

We would like to propose an alternative:

  Product       : {product.title()}
  Quantity      : {quantity} kg
  Counter Price : ₹{counter_price}/kg  (your offer: ₹{price}/kg)

Please log in to the platform to respond or submit a new offer.

Best regards,
Procurement Team
"""

    else:
        return False

    return _send(user_email, subject, body)


# ── Feature: Notify admin when user responds to counter offer ─────────────────

def notify_admin_counter_response(admin_email, user_name, user_email,
                                   product, quantity, counter_price, response):
    """
    Sent to admin when a user accepts or declines a counter offer.
    response = 'accepted' or 'declined'
    """
    emoji   = "✅" if response == "accepted" else "❌"
    verb    = "ACCEPTED" if response == "accepted" else "DECLINED"

    subject = f"{emoji} Counter Offer {verb} — {product.title()} | {user_name}"
    body = f"""Hello Admin,

A user has responded to your counter offer.

  Response  : {verb}
  User      : {user_name} ({user_email})
  Product   : {product.title()}
  Quantity  : {quantity} kg
  Your Price: ₹{counter_price}/kg

{"✅ Please proceed with fulfilment and contact the user." if response == "accepted" else "❌ The user has declined. Consider revising your offer or closing the deal."}

Log in to the admin panel to take further action.

VendorIQ System
"""
    return _send(admin_email, subject, body)