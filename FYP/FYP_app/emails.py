from django.core.mail import send_mail
from django.conf import settings
from django.core.signing import TimestampSigner
import logging

logger = logging.getLogger(__name__)
nominee_signer = TimestampSigner()

# ──────────────────────────────────────────────
# 1. TWO-FACTOR SECURITY VERIFICATION (OTP)
# ──────────────────────────────────────────────

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
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=False)
        logger.info(f"OTP email logged cleanly for address: {user_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to log security OTP email payload: {e}")
        return False


def build_nominee_confirmation_url(role):
    token = nominee_signer.sign(
        f"{role.id}:{role.invitation_token}:{role.nominee.nominee_email}"
    )
    return f"{settings.FRONTEND_URL}/nominee-invitation/{token}"


def send_nominee_invitation_email(role, owner_name):
    nominee = role.nominee
    confirmation_url = build_nominee_confirmation_url(role)
    role_name = role.get_role_display().lower()
    subject = f"Confirm your {role_name} role in {owner_name}'s Digital Vault"
    message = (
        f"Hello {nominee.nominee_name},\n\n"
        f"{owner_name} has invited you to be a {role_name} in their Trusted Circle. "
        "This invitation is only for the role named above; any other role has a separate decision.\n\n"
        f"Confirm here: {confirmation_url}\n\n"
        "The link expires in seven days. Opening the link will not accept the invitation; "
        "you will be asked to make an explicit choice.\n\n"
        "Regards,\nDigital Vault Team"
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [nominee.nominee_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send nominee invitation: {e}")
        return False


# ──────────────────────────────────────────────
# 2. ESCALATION & DECISION TRIGGERS (KILLSWITCH)
# ──────────────────────────────────────────────

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


def send_nominee_verification_email(role, owner_name):
    """Ask one accepted witness to record an explicit death/alive vote."""
    nominee = role.nominee
    subject = f"🔐 Verification Required: Digital Legacy Status for {owner_name}"
    confirmation_url = f"{settings.FRONTEND_URL}/witness-confirmation/{role.vote_token}"
    message = (
        f"Dear {nominee.nominee_name},\n\n"
        f"{owner_name} has not checked in. As an accepted death witness, please review "
        "the request and explicitly confirm whether they are alive or have passed away.\n\n"
        f"Review and respond: {confirmation_url}\n\n"
        "Legacy assets remain locked until the required witness quorum confirms death. "
        "This link is personal to your witness role.\n\n"
        f"Regards,\nDigital Vault Automation Core"
    )
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [nominee.nominee_email],
            fail_silently=False,
        )
        logger.info("Witness verification email dispatched to nominee id %s", nominee.id)
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch verification email: {e}")
        return False

