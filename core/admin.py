from django.contrib import admin
from decimal import Decimal
from .utils import create_owner_log,create_notification
from .models import PaymentMethod, Deposit, Withdrawal, InvestmentPlan, UserInvestment,TransactionLog


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']

# DEPOSIT ADMIN

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'amount',
        'method',
        'status',
        'credited',
        'referral_bonus_paid',
        'admin_note',
        'created_at'
    ]

    list_filter = [
        'status',
        'credited'
    ]

    search_fields = [
        'user__username',
        'user__email'
    ]

    fields = [
        'user',
        'amount',
        'method',
        'proof',
        'status',
        'admin_note'
    ]

    def save_model(self, request, obj, form, change):

        old_status = None

        if change:
            old = Deposit.objects.get(pk=obj.pk)
            old_status = old.status

            
            # APPROVE DEPOSIT
            
            if (
                old.status != "Approved"
                and obj.status == "Approved"
                and not obj.credited
            ):

                user = obj.user

                # credit wallet
                user.wallet_balance += Decimal(obj.amount)
                user.save()

                obj.credited = True

                # first deposit referral bonus
                approved_count = Deposit.objects.filter(
                    user=user,
                    status="Approved"
                ).exclude(pk=obj.pk).count()

                if (
                    approved_count == 0
                    and user.referred_by
                    and not obj.referral_bonus_paid
                ):

                    referrer = user.referred_by
                    bonus = Decimal(obj.amount) * Decimal("0.05")

                    referrer.wallet_balance += bonus
                    referrer.save()

                    obj.referral_bonus_paid = True

                    # referral log
                    TransactionLog.objects.create(
                        user=referrer,
                        tx_type='Bonus',
                        amount=bonus,
                        status='Success',
                        description=f'Referral bonus from {user.username}'
                    )
                create_notification(
                    user=user,
                    title="Deposit Approved",
                    message=(
                        f"Your deposit of "
                        f"${obj.amount} "
                        f"has been approved."
                    )
                )
                # =========================
                # OWNER ACTION LOG
                # =========================

                create_owner_log(
                    owner=request.user,
                    action="Deposit Approved",
                    description=(
                        f"Approved deposit of "
                        f"${obj.amount} for "
                        f"{user.username}"
                    ),
                    target_user=user
                )


            # =========================
            # DEPOSIT REJECTED
            # =========================

            if (
                old.status != "Rejected"
                and obj.status == "Rejected"
            ):

                create_owner_log(
                    owner=request.user,
                    action="Deposit Rejected",
                    description=(
                        f"Rejected deposit of "
                        f"${obj.amount} for "
                        f"{obj.user.username}"
                    ),
                    target_user=obj.user
                )

                create_notification(
                    user=obj.user,
                    title="Deposit Rejected",
                    message=(
                        f"Your deposit of "
                        f"${obj.amount} "
                        f"was rejected."
                    )
                )

        super().save_model(request, obj, form, change)

        
        # UPDATE TRANSACTION LOG
        
        log = TransactionLog.objects.filter(
            user=obj.user,
            tx_type='Deposit',
            amount=obj.amount
        ).order_by('-id').first()

        if log:

            if obj.status == "Approved":
                log.status = "Success"
                log.description = (
                    obj.admin_note
                    if obj.admin_note
                    else "Deposit approved"
                )

            elif obj.status == "Rejected":
                log.status = "Rejected"
                log.description = (
                    obj.admin_note
                    if obj.admin_note
                    else "Deposit rejected"
                )

            else:
                log.status = "Pending"

            log.save()



# WITHDRAWAL ADMIN

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'amount',
        'method',
        'status',
        'deducted',
        'admin_note',
        'created_at'
    ]

    list_filter = [
        'status',
        'deducted'
    ]

    search_fields = [
        'user__username',
        'user__email'
    ]

    fields = [
        'user',
        'amount',
        'method',
        'account_details',
        'status',
        'admin_note'
    ]

    def save_model(self, request, obj, form, change):

        old_status = None

        if change:
            old = Withdrawal.objects.get(pk=obj.pk)
            old_status = old.status

            
            # APPROVE WITHDRAWAL
            
            if (
                old.status != "Approved"
                and obj.status == "Approved"
                and not obj.deducted
            ):

                obj.deducted = True

                # =========================
                # OWNER ACTION LOG
                # =========================

                create_owner_log(
                    owner=request.user,
                    action="Withdrawal Approved",
                    description=(
                        f"Approved withdrawal of "
                        f"${obj.amount} for "
                        f"{obj.user.username}"
                    ),
                    target_user=obj.user
                )

                create_notification(
                    user=user,
                    title="Withdrawal Approved",
                    message=(
                        f"Your withdrawal of "
                        f"${obj.amount} "
                        f"has been approved."
                    )
                )

            
            # REJECTED = REFUND
            
            if (
                old.status == "Pending"
                and obj.status == "Rejected"
            ):

                user = obj.user
                user.wallet_balance += Decimal(obj.amount)
                user.save()

                # =========================
                # OWNER ACTION LOG
                # =========================

                create_owner_log(
                    owner=request.user,
                    action="Withdrawal Rejected",
                    description=(
                        f"Rejected withdrawal of "
                        f"${obj.amount} for "
                        f"{user.username}"
                    ),
                    target_user=user
                )

                create_notification(
                    user=obj.user,
                    title="Withdrawal Rejected",
                    message=(
                        f"Your withdrawal of "
                        f"${obj.amount} "
                        f"was rejected."
                    )
                )

        super().save_model(request, obj, form, change)

        
        # UPDATE TRANSACTION LOG
        
        log = TransactionLog.objects.filter(
            user=obj.user,
            tx_type='Withdrawal',
            amount=obj.amount
        ).order_by('-id').first()

        if log:

            if obj.status == "Approved":
                log.status = "Success"
                log.description = (
                    obj.admin_note
                    if obj.admin_note
                    else "Withdrawal approved"
                )

            elif obj.status == "Rejected":
                log.status = "Rejected"
                log.description = (
                    obj.admin_note
                    if obj.admin_note
                    else "Withdrawal rejected"
                )

            else:
                log.status = "Pending"

            log.save()


@admin.register(InvestmentPlan)
class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'min_amount',
        'max_amount',
        'daily_roi',
        'duration_days',
        'is_active'
    ]


from .models import KYCSubmission

@admin.register(KYCSubmission)
class KYCSubmissionAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'status',
        'submitted_at',
        'reviewed_at'
    )

    list_filter = (
        'status',
    )

    search_fields = (
        'user__username',
        'user__email'
    )


admin.site.register(TransactionLog)
admin.site.register(UserInvestment)