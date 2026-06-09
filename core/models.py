from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()



class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    wallet_address = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Deposit(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE
    )

    proof = models.ImageField(
        upload_to='deposits/',
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    admin_note = models.TextField(
        blank=True,
        null=True
    )

    referral_bonus_paid = models.BooleanField(default=False)
    credited = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        # detect approval and credit once
        if self.pk:
            old = Deposit.objects.get(pk=self.pk)

            if (
                old.status != 'Approved'
                and self.status == 'Approved'
                and not self.credited
            ):
                self.user.wallet_balance += Decimal(self.amount)
                self.user.save()
                self.credited = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.amount}"


class Withdrawal(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    method = models.CharField(max_length=100)
    account_details = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    admin_note = models.TextField(
        blank=True,
        null=True
    )

    deducted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount}"


class InvestmentPlan(models.Model):
    name = models.CharField(max_length=100)

    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    daily_roi = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    duration_days = models.IntegerField()

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.name



class UserInvestment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    plan = models.ForeignKey(
        InvestmentPlan,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    start_date = models.DateTimeField(auto_now_add=True)

    last_claim = models.DateTimeField(
        auto_now_add=True
    )

    days_paid = models.IntegerField(default=0)

    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class TransactionLog(models.Model):

    TYPE_CHOICES = (
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
        ('Investment', 'Investment'),
        ('Profit', 'Profit'),
        ('Bonus', 'Bonus'),
        ('Return', 'Return'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    tx_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Success'
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.tx_type}"


class SiteSettings(models.Model):

    maintenance_mode = models.BooleanField(
        default=False
    )

    deposits_enabled = models.BooleanField(
        default=True
    )

    withdrawals_enabled = models.BooleanField(
        default=True
    )

    investments_enabled = models.BooleanField(
        default=True
    )

    site_announcement = models.TextField(
        blank=True,
        null=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return "Platform Settings"



class Notification(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class OwnerActionLog(models.Model):

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    action = models.CharField(
        max_length=255
    )

    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='target_logs'
    )

    description = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.owner} - {self.action}"


class BroadcastMessage(models.Model):

    PRIORITY_CHOICES = (
        ('Normal', 'Normal'),
        ('Important', 'Important'),
        ('Critical', 'Critical'),
    )

    TARGET_CHOICES = (
        ('All', 'All Users'),
        ('Investors', 'Investors'),
        ('Active', 'Active Users'),
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='Normal'
    )

    target_audience = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default='All'
    )

    is_active = models.BooleanField(
        default=True
    )

    is_pinned = models.BooleanField(
        default=False
    )

    start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    dismissible = models.BooleanField(
        default=True
    )

    send_as_notification = models.BooleanField(
        default=False
    )

    send_email = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.title


class SecurityLog(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    action = models.CharField(
        max_length=255
    )

    details = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.action}"


class KYCSubmission(models.Model):

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    id_document = models.ImageField(
        upload_to='kyc/id/'
    )

    selfie = models.ImageField(
        upload_to='kyc/selfie/'
    )

    address_proof = models.ImageField(
        upload_to='kyc/address/'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    admin_note = models.TextField(
        blank=True,
        null=True
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.user.username} KYC"