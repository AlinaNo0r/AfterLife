from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


def only_alphabets(value):

    if not value.replace(" ", "").isalpha():
        raise ValidationError("Only alphabets are allowed in the name.")

# Create your models here.



class User(AbstractUser):
    DOB = models.DateField(null=True, blank=True)
    Gender = models.CharField(max_length=10, blank=True)
    phone= models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username
    
class Nominee(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nominees')
    nominee_name = models.CharField(max_length=100, validators=[only_alphabets])
    nominee_email = models.EmailField()
    nominee_phone = models.CharField(max_length=15)
    relationship = models.CharField(max_length=50)

    def __str__(self):
        return self.nominee_name

class Credentials(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credentials')
    Platform_URL = models.URLField()
    UserName = models.CharField(max_length=100)
    Email = models.EmailField()
    Password = models.CharField(max_length=255)
    Nominee = models.ForeignKey(Nominee, on_delete=models.PROTECT, related_name='credentials')
    
    class Meta:
        unique_together = ['user', 'Platform']

    def __str__(self):
        return f"{self.Platform}"
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_login = models.DateTimeField(default=timezone.now)
    login_interval = models.IntegerField(default=7)  # days
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('warning', 'Warning'), ('inactive', 'Inactive')], default='active')
    warning_start = models.DateTimeField(null=True, blank=True)


class VaultItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='vault_videos/')
    scheduled_date = models.DateField()
    recipient_email = models.EmailField()
    is_sent = models.BooleanField(default=False)


class ChatMemory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_message = models.TextField()
    bot_response = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} — {self.timestamp.strftime('%Y-%m-%d %H:%M')}"