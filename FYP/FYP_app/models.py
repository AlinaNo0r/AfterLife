
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
import os
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Validators
# ──────────────────────────────────────────────

def only_alphabets(value):
    """Allow letters and spaces only; rejects empty / whitespace-only strings."""
    stripped = value.strip()
    if not stripped or not stripped.replace(" ", "").isalpha():
        raise ValidationError("Only alphabets are allowed in the name.")


def validate_video(value):
    """Accept common video file extensions only."""
    ext = os.path.splitext(value.name)[1].lower()
    allowed = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    if ext not in allowed:
        raise ValidationError(
            f"Unsupported file type '{ext}'. Allowed types: {', '.join(allowed)}"
        )


# ──────────────────────────────────────────────
# User
# ──────────────────────────────────────────────

class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Fields use snake_case to follow Django/DRF conventions.
    """
    dob = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    gender = models.CharField(choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], max_length=10, blank=True, default='')
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username


# ──────────────────────────────────────────────
# Nominee
# ──────────────────────────────────────────────

class Nominee(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='nominees'
    )
    nominee_name = models.CharField(max_length=100, validators=[only_alphabets])
    nominee_email = models.EmailField()
    nominee_phone = models.CharField(max_length=15)
    relationship = models.CharField(max_length=50, choices=[
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('friend', 'Friend'),
        ('other', 'Other')
    ])

    def __str__(self):
        return self.nominee_name


# ──────────────────────────────────────────────
# NomineeRole
# ──────────────────────────────────────────────

class NomineeRole(models.Model):
    ROLE_CHOICES = [
        ('witness', 'Death Witness'),
        ('beneficiary', 'Beneficiary'),
    ]
    nominee = models.ForeignKey(
        Nominee, on_delete=models.CASCADE, related_name='roles'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['nominee', 'role']

    def __str__(self):
        return f"{self.nominee.nominee_name} — {self.get_role_display()}"


# ──────────────────────────────────────────────
# Credentials
# ──────────────────────────────────────────────

class Credentials(models.Model):
    """
    Stores third-party platform credentials for a user.

    IMPORTANT: The `password` field should be encrypted at rest.
    Install django-encrypted-model-fields and replace CharField with
    EncryptedCharField once you configure FIELD_ENCRYPTION_KEY in settings.

        pip install django-encrypted-model-fields

        # settings.py
        FIELD_ENCRYPTION_KEY = os.environ['FIELD_ENCRYPTION_KEY']  # 32-byte Fernet key

        # then swap:
        from encrypted_model_fields.fields import EncryptedCharField
        password = EncryptedCharField(max_length=255)
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='credentials'
    )
    platform = models.CharField(max_length=100)
    platform_url = models.URLField()
    username_on_platform = models.CharField(max_length=100)
    email_on_platform = models.EmailField()

    #   Replace with EncryptedCharField in production (see docstring above)
    password = models.CharField(max_length=255)

    assigned_nominee = models.ForeignKey(
        Nominee, on_delete=models.PROTECT, related_name='credentials'
    )

    class Meta:
        unique_together = ['user', 'platform']
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"

    def __str__(self):
        return self.platform


# ──────────────────────────────────────────────
# UserProfile
# ──────────────────────────────────────────────

class UserProfile(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('warning', 'Warning'),
        ('inactive', 'Inactive'),
    ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    last_seen = models.DateTimeField(default=timezone.now)
    timeout_days = models.IntegerField(default=7)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='active'
    )
    warning_start = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} — {self.get_status_display()}"
    
    # ──────────────────────────────────────────────
    # Killswitch Methods
    # ──────────────────────────────────────────────

    def notify_nominees_warning(self):
        
        from django.core.mail import send_mail
        from django.conf import settings
    
       
        witnesses = self.user.nominees.filter(
        roles__role='witness'
        ).prefetch_related('roles')

        if not witnesses.exists():
            logger.warning(f"No witnesses found for user {self.user.username}")
            return

        for nominee in witnesses:
            try:
                subject = f"[URGENT] {self.user.get_full_name()} has not checked in"
                confirmation_link = f"{settings.SITE_URL}/api/confirm-death/{self.user.id}/"
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
                    fail_silently=False,   # Error aaye to exception dikhega
                )
                
                logger.info(f"Warning email sent to {nominee.nominee_name} for {self.user.username}")
                
            except Exception as e:
                logger.error(f"Failed to send email to {nominee.nominee_email}: {e}")

        logger.info(f"✅ Warning emails sent to {witnesses.count()} witness(es) for {self.user.username}")

# ──────────────────────────────────────────────
# VaultItem
# ──────────────────────────────────────────────

class VaultItem(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='vault_items'
    )
    title = models.CharField(max_length=200)
    video_file = models.FileField(
        upload_to='vault_videos/', validators=[validate_video]
    )
    scheduled_date = models.DateField()
    recipient = models.ForeignKey(
        Nominee, on_delete=models.PROTECT, related_name='vault_items'
    )
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} → {self.recipient.nominee_name}"


# ──────────────────────────────────────────────
# ChatMemory
# ──────────────────────────────────────────────

class ChatMemory(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='chat_memories'
    )
    original_message = models.TextField()
    bot_response = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} — {self.timestamp.strftime('%Y-%m-%d %H:%M')}"