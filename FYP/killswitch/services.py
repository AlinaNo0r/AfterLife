from django.core.mail import send_mail
from django.conf import settings
import logging
logger = logging.getLogger(__name__)
from FYP_app.models import Nominee, NomineeRole, VaultItem, ChatMemory, UserProfile, Credentials


def notify_nominees_warning(self):
        
        witnesses = self.user.nominees.filter(
        roles__role='witness'
        ).prefetch_related('roles')

        if not witnesses.exists():
            logger.warning(f"No witnesses found for user {self.user.username}")
            return

        for nominee in witnesses:
            try:
                subject = f"[URGENT] {self.user.get_full_name()} has not checked in"
                confirmation_link = f"{settings.FRONTEND_URL}/confirm-witness/{UserProfile.witness_token}/"
                message = f"""Dear {nominee.nominee_name},

                {self.user.get_full_name()} has not checked in for {self.timeout_days} days.

                As a designated Death Witness, we need you to confirm their status.

                Please log in to Digital Vault and confirm:
                1. If they are alive and well → This will reset the timer.
                2. If they are unresponsive → This will trigger the next steps in the process
                {confirmation_link}

                If no action is taken within 7 days, the system will proceed automatically.

                Death Vault Team
                """

                send_mail(
                    subject=subject.strip(),
                    message=message.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[nominee.nominee_email],
                    fail_silently=False,   
                )
                
                logger.info(f"Warning email sent to {nominee.nominee_name} for {self.user.username}")
                
            except Exception as e:
                logger.error(f"Failed to send email to {nominee.nominee_email}: {e}")

        logger.info(f" Warning emails sent to {witnesses.count()} witness(es) for {self.user.username}")




def release_assets(profile):
    nominees = Nominee.objects.filter(user=profile.user)
    
    for nominee in nominees:
        is_beneficiary = nominee.roles.filter(role='beneficiary').exists()
        
        if not is_beneficiary:
            continue
        

        vault_items = VaultItem.objects.filter(recipient=nominee, is_sent=False)
        for item in vault_items:
            item.is_sent = True
            item.save()
        
        
        credentials = Credentials.objects.filter(assigned_nominee=nominee, status='locked')
        for cred in credentials:
            cred.status = 'released'
            cred.save()
        
        
        ChatMemory.objects.filter(user=profile.user).update(accessible_to_nominees=True)
        
        
        total_items = vault_items.count() + credentials.count()
        send_release_notification_email(nominee, total_items)
    
    print(f"Assets released for {profile.user.username}")

def send_release_notification_email(nominee, item_count):
    
    send_mail(
        subject='Digital Vault - Assets Have Been Released',
        message=(
            f"Dear {nominee.nominee_name},\n\n"
            f"The assets entrusted to you have now been released. "
            f"{item_count} item(s) are now accessible.\n\n"
            f"Please log in to view them."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[nominee.nominee_email],
    )
###++++++++++++++++++++++++++++++++++++++++
###    Vault items logic 
####++++++++++++++++++++++++++++++++++++++++
from datetime import date

def check_scheduled_releases():
    from FYP_app.models import VaultItem

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
    )