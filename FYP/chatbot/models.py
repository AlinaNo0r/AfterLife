from django.conf import settings
from django.db import models


class MemorySource(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='legacy_memory_sources',
    )
    beneficiaries = models.ManyToManyField(
        'FYP_app.Nominee',
        related_name='legacy_memory_sources',
    )
    display_name = models.CharField(max_length=200)
    file = models.FileField(
        upload_to='legacy_ai_sources/%Y/%m/',
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default='processing',
    )
    error_message = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        return super().delete(*args, **kwargs)


class MemoryChunk(models.Model):
    source = models.ForeignKey(
        MemorySource,
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    text = models.TextField()
    category = models.CharField(max_length=40)
    word_count = models.PositiveIntegerField()
    embedding = models.JSONField()


class BeneficiaryPersona(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='legacy_personas',
    )
    nominee = models.OneToOneField(
        'FYP_app.Nominee',
        on_delete=models.CASCADE,
        related_name='legacy_persona',
    )
    bond_context = models.TextField(blank=True)
    voice_preferences = models.CharField(max_length=500, blank=True)
    spirituality_enabled = models.BooleanField(default=False)
    faith_tradition = models.CharField(max_length=120, blank=True)
    beneficiary_spirituality_enabled = models.BooleanField(default=False)
    beneficiary_faith_tradition = models.CharField(max_length=120, blank=True)
    owner_data_consent_at = models.DateTimeField(null=True, blank=True)
    beneficiary_processing_consent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class LegacyConversation(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='legacy_conversations',
    )
    nominee = models.ForeignKey(
        'FYP_app.Nominee',
        on_delete=models.CASCADE,
        related_name='legacy_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'nominee'],
                name='unique_legacy_conversation_per_beneficiary',
            )
        ]


class LegacyMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'Beneficiary'),
        ('assistant', 'Legacy AI'),
    ]

    conversation = models.ForeignKey(
        LegacyConversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
