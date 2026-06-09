from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username',
        'email',
        'wallet_balance',
        'kyc_verified',
        'is_verified',
        'is_suspended',
        'is_staff',
    )

    fieldsets = UserAdmin.fieldsets + (

        (
            'OneMarketX Account',
            {
                'fields': (
                    'wallet_balance',
                    'withdrawal_pin',
                    'kyc_verified',
                    'is_verified',
                    'is_suspended',
                    'suspension_reason',
                    'referral_code',
                    'referred_by',
                    'last_password_change',
                    'last_email_change',
                    'claim_streak',
                    'last_streak_claim',
                )
            }
        ),

    )