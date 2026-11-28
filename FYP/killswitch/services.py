import logging
from datetime import date

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from FYP_app.models import VaultItem

logger = logging.getLogger(__name__)
token_generator = PasswordResetTokenGenerator()


def send_release_notification_email(nominee, item_count, legacy_ai_available=False):
    login_account = nominee.login_account
    released_content = []
    if item_count:
        released_content.append(f'{item_count} item(s) are now accessible.')
    if legacy_ai_available:
        chat_url = f'{settings.FRONTEND_URL}/beneficiary/legacy-chat'
        released_content.append(
            'Legacy AI access is available after you sign in and review the third-party '
            f'data-processing notice:\n{chat_url}'
        )
    released_summary = '\n\n'.join(released_content)
    if login_account:
        uid = urlsafe_base64_encode(force_bytes(login_account.pk))
        token = token_generator.make_token(login_account)
        set_password_link = f"{settings.FRONTEND_URL}/set-password/{uid}/{token}/"
        message = (
            f"Dear {nominee.nominee_name},\n\n"
            "The items or Legacy AI access entrusted to you are now available.\n"
            f"{released_summary}\n\n"
            "Set your password using this link:\n"
            f"{set_password_link}\n\n"
            "Digital Vault Team"
        )
    else:
        message = (
            f"Dear {nominee.nominee_name},\n\n"
            "The items or Legacy AI access entrusted to you are now available.\n"
            f"{released_summary}\n\n"
            "Please log in to view them.\n\n"
            "Digital Vault Team"
        )

    try:
        send_mail(
            subject='Digital Vault - Assets Have Been Released',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[nominee.nominee_email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Could not send release notice for nominee id %s", nominee.id)
        return False


def check_scheduled_releases():
    today = date.today()
    eligible_items = VaultItem.objects.filter(
        recipient__roles__role='beneficiary',
        recipient__roles__consent_status='accepted',
    ).distinct()

    scheduled_items = eligible_items.filter(
        release_type='scheduled',
        scheduled_date__lte=today,
        is_sent=False,
    )
    for item in scheduled_items:
        if send_item_release_email(item):
            item.is_sent = True
            item.save(update_fields=['is_sent'])

    recurring_items = eligible_items.filter(
        release_type='recurring',
        scheduled_date__lte=today,
    )
    for item in recurring_items:
        if item.recurring_interval_days is None:
            logger.error(
                "Skipping recurring vault item %s without an interval",
                item.id,
            )
            continue
        due = (
            item.last_sent_at is None
            or (today - item.last_sent_at).days >= item.recurring_interval_days
        )
        if due and send_item_release_email(item):
            item.last_sent_at = today
            item.save(update_fields=['last_sent_at'])


def send_item_release_email(item):
    try:
        send_mail(
            subject=f'Digital Vault - "{item.title}" Has Been Released',
            message=(
                f"Dear {item.recipient.nominee_name},\n\n"
                f"A new item titled \"{item.title}\" has been released to you.\n\n"
                "Please log in to view it."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[item.recipient.nominee_email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Could not send release notice for vault item id %s", item.id)
        return False
