from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# ----------------------------------------
#               OTP Message
# ----------------------------------------

def send_otp_email(user_email, otp_code, execution_purpose):
    """
    Dispatches a secure 6-digit temporary verification token to the user's mailbox.
    """

    if execution_purpose == 'register':
        subject = "🔑 Activate Your Digital Vault Account: Verification OTP"
        body_context = "Complete your registration profile setup."
    else:
        subject = "🛡️ Secure 2FA Login Verification Passcode"
        body_context = "Authorize your account dashboard login attempt."

    message = (
        f"Hello,\n\n"
        f"Your temporary secure 6-digit verification passcode is: {otp_code}\n\n"
        f"Please enter this numeric code inside the web interface to {body_context}\n"
        f"This security code is highly time-sensitive and will permanently expire in 5 minutes.\n\n"
        f"If you did not initiate this system request, please update your master credentials immediately.\n\n"
        f"Regards,\nDigital Vault Security Core"
    )

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email]. fail_silently=False)
         logger.info(f"OTP email logged cleanly for address: {user_email}")
         return True

    except Exception as e:
        logger.error(f"Failed to log security OTP email payload: {e}")
        return False


# -----------------------------------------------------------------
# Messages for sending warning Notification
# ------------------------------------------------------------------
def send_legacy_warning_email(user_email, username, total_days_missed):
    """Fires warning alert notice to the owner when inactivity threshold breaks."""
    subject = "⚠️ URGENT: Inactivity Detected on Your Afterlife Account"
    message = (
        f"Hello {username},\n\n"
        f"Our system has detected that you have not checked in for {total_days_missed} days.\n"
        f"Your account status has been changed to WARNING.\n\n"
        f"Please log into the app or tap the 'Stay Alive' button within the next 7 days.\n"
        f"If you do not check in, your digital legacy execution will begin automatically.\n\n"
        f"Regards,\nDigital Vault Security Team"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Failed to send warning email: {e}")
        return False


def send_nominee_verification_email(nominee_email, nominee_name, owner_name, profile_id):
    """Sends confirmation query containing execution paths directly to the Nominee."""
    subject = f"🔐 Verification Required: Digital Legacy Status for {owner_name}"
    
    # Generate fallback links pointing directly to your local development host server endpoints
    alive_link = f"http://127.0.0{profile_id}/"
    deceased_link = f"http://127.0.0{profile_id}/"
    
    message = (
        f"Dear {nominee_name},\n\n"
        f"You have been designated as a trusted legacy beneficiary by {owner_name}.\n"
        f"The owner has been unresponsive. We require you to verify their status:\n\n"
        f"👉 IF THEY ARE ALIVE & WELL (Extends countdown by 7 days):\n"
        f"{alive_link}\n\n"
        f"👉 IF THEY HAVE PASSED AWAY (Activates Vault Release / AI Chatbot Branch):\n"
        f"{deceased_link}\n\n"
        f"Please act promptly to ensure secure data preservation transmission pipelines.\n\n"
        f"Regards,\nDigital Vault Automation Core"
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [nominee_email], fail_silently=False)
        logger.info(f"Verification email dispatched to nominee: {nominee_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch verification email: {e}")
        return False


def send_final_vault_payload(nominee_email, nominee_name, platform, username, password):
    """Delivers the actual decrypted legacy data block directly to the authorized beneficiary."""
    subject = "🔑 Secure Legacy Asset Handover: Credentials Released"
    message = (
        f"Dear {nominee_name},\n\n"
        f"Pursuant to the validated legacy protocol execution rules, the secure vault has unlocked your assigned assets.\n\n"
        f"--- VAULT ITEM ENTRY ---\n"
        f"Platform Domain: {platform}\n"
        f"Username ID: {username}\n"
        f"Decrypted Password: {password}\n"
        f"------------------------\n\n"
        f"Please record these credentials immediately. This packet is fully encrypted at rest on disk.\n\n"
        f"Regards,\nDigital Vault Core"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [nominee_email])

