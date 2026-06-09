from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    claim_streak = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    is_suspended = models.BooleanField(default=False)
    withdrawal_pin = models.CharField(
    max_length=128,
    blank=True,
    null=True
    )

    kyc_verified = models.BooleanField(
        default=False
    )

    last_password_change = models.DateTimeField(
        null=True,
        blank=True
    )

    last_email_change = models.DateTimeField(
        null=True,
        blank=True
    )

    suspension_reason = models.TextField(
        blank=True,
        null=True
    )

    wallet_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )

    
    last_streak_claim = models.DateField(
        null=True,
        blank=True
    )

    referral_code = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        null=True
    )

    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = get_random_string(8).upper()
        super().save(*args, **kwargs)