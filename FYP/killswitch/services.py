import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils import timezone
from datetime import date
import logging

from FYP_app.models import Nominee, NomineeRole, VaultItem, ChatMemory, UserProfile, Credentials

logger = logging.getLogger(__name__)
token_generator = PasswordResetTokenGenerator()


def notify_nominees_warning(self):
    witnesses = self.user.nominees.filter(
        roles__role='witness'
    ).prefetch_related('roles')

    # User ko khud bhi reminder bhejo
    try:
        send_mail(
            subject="[URGENT] You have not checked in",
            message=(
                f"Dear {self.user.get_full_name()},\n\n"
                f"You have not checked in for {self.timeout_days} days.\n\n"
                f"Please log in and confirm you're active, or your assets may be released "
                f"to your beneficiaries after the warning period.\n\n"
                f"Digital Vault Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
            fail_silently=False,
        )
        logger.info(f"Self-reminder email sent to {self.user.email}")
    except Exception as e:
        logger.error(f"Failed to send self-reminder to {self.user.email}: {e}")

    if not witnesses.exists():
        logger.warning(f"No witnesses found for user {self.user.username}")
        return

    for nominee in witnesses:
        try:
            role = nominee.roles.filter(role='witness').first()
            if not role:
                continue

            # naya vote_token har baar generate karo taake purane votes na dohrayein
            role.vote_token = uuid.uuid4()
            role.vote = None
            role.save()

            death_link = f"{settings.FRONTEND_URL}/vote-death/{role.vote_token}/"
            alive_link = f"{settings.FRONTEND_URL}/vote-alive/{role.vote_token}/"

            message = f"""Dear {nominee.nominee_name},

{self.user.get_full_name()} has not checked in for {self.timeout_days} days.

1. If they are alive and well:
{alive_link}

2. If they are unresponsive (confirm death):
{death_link}

Digital Vault Team
"""
            send_mail(
                subject=f"[URGENT] {self.user.get_full_name()} has not checked in",
                message=message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[nominee.nominee_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send email to {nominee.nominee_email}: {e}")


def release_assets(profile):
    nominees = Nominee.objects.filter(user=profile.user)

    for nominee in nominees:
        is_beneficiary = nominee.roles.filter(role='beneficiary').exists()
        if not is_beneficiary:
            continue

        # Vault Items release
        vault_items = VaultItem.objects.filter(recipient=nominee, is_sent=False)
        for item in vault_items:
            item.is_sent = True
            item.save()

        # Credentials release
        credentials = Credentials.objects.filter(assigned_nominee=nominee, status='locked')
        for cred in credentials:
            cred.status = 'released'
            cred.save()

        # Chat Memory accessible
        ChatMemory.objects.filter(user=profile.user).update(accessible_to_nominees=True)

        total_items = vault_items.count() + credentials.count()

        # Release notification + Password Set email
        send_release_notification_email(nominee, total_items)

    print(f"Assets released for {profile.user.username}")


def send_release_notification_email(nominee, item_count):
    """
    Release hone pe email bhejta hai + agar login_account hai to Password Set link bhi bhejta hai
    """
    login_account = nominee.login_account

    if login_account:
        uid = urlsafe_base64_encode(force_bytes(login_account.pk))
        token = token_generator.make_token(login_account)
        set_password_link = f"{settings.FRONTEND_URL}/set-password/{uid}/{token}/"

        message = f"""Dear {nominee.nominee_name},

The assets entrusted to you have now been released.
{item_count} item(s) are now accessible.

To access them, please set your password first by clicking the link below:

{set_password_link}

This link is valid for limited time only.

Digital Vault Team
"""
    else:
        message = f"""Dear {nominee.nominee_name},

The assets entrusted to you have now been released.
{item_count} item(s) are now accessible.

Please log in to view them.

Digital Vault Team
"""

    send_mail(
        subject='Digital Vault - Assets Have Been Released',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[nominee.nominee_email],
        fail_silently=False,
    )


def check_scheduled_releases():
    today = date.today()

    # 1. One-time scheduled items
    scheduled_items = VaultItem.objects.filter(
        release_type='scheduled',
        scheduled_date__lte=today,
        is_sent=False
    )
    for item in scheduled_items:
        send_item_release_email(item)
        item.is_sent = True
        item.save()
        print(f"Scheduled item '{item.title}' released to {item.recipient.nominee_name}")

    # 2. Recurring items
    recurring_items = VaultItem.objects.filter(
        release_type='recurring',
        scheduled_date__lte=today
    )
    for item in recurring_items:
        if item.last_sent_at is None:
            due = True
        else:
            days_since = (today - item.last_sent_at).days
            due = days_since >= item.recurring_interval_days

        if due:
            send_item_release_email(item)
            item.last_sent_at = today
            item.save()
            print(f"Recurring item '{item.title}' released to {item.recipient.nominee_name}")


def send_item_release_email(item):
    send_mail(
        subject=f'Digital Vault - "{item.title}" Has Been Released',
        message=(
            f"Dear {item.recipient.nominee_name},\n\n"
            f"A new item titled \"{item.title}\" has been released to you.\n\n"
            f"Please log in to view it."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[item.recipient.nominee_email],
        fail_silently=False,
    )


def release_assets_for_single_nominee(nominee):
    vault_items = VaultItem.objects.filter(recipient=nominee, is_sent=False)
    for item in vault_items:
        item.is_sent = True
        item.save()

    credentials = Credentials.objects.filter(assigned_nominee=nominee, status='locked')
    for cred in credentials:
        cred.status = 'released'
        cred.save()

    total_items = vault_items.count() + credentials.count()
    send_release_notification_email(nominee, total_items)

    print(f"Assets released to {nominee.nominee_name} (individual confirmation).")