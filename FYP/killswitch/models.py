from django.db import models
from FYP_app.models import User, Nominee, UserProfile


class DeathConfirmation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    confirmed_by = models.ForeignKey(Nominee, on_delete=models.CASCADE)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)


class Witness(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='witnesses'
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'email')  

    def __str__(self):
        return f"{self.name} ({self.email}) — Witness of {self.user.username}"

