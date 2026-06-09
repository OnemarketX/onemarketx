from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.mail import send_mail
import random
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from .models import KYCSubmission
from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.hashers import (
    check_password
)
from .utils import create_owner_log
from .utils import get_site_settings
from django.db.models import Count
from django.contrib import messages
from .utils import create_notification
from .models import SecurityLog
from django.shortcuts import get_object_or_404
from .models import (
    PaymentMethod,
    Deposit,
    Withdrawal,
    InvestmentPlan,
    UserInvestment,
    TransactionLog,
    SiteSettings,
    Notification,
    OwnerActionLog,
    BroadcastMessage,
)

from .decorators import (
    superuser_required,
    staff_required
)


def home(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')


def contact(request):
    return render(request, 'contact.html')


def terms(request):
    return render(request, 'terms.html')


def privacy(request):
    return render(request, 'privacy.html')


def faq(request):
    return render(request, 'faq.html')


@login_required(login_url='/login/')
def dashboard_view(request):

    settings_obj = get_site_settings()

    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return render(
        request,
        'dashboard/home.html',
        {
            'settings_obj': settings_obj,

            'unread_notifications':
            unread_notifications
        }
    )



# DEPOSIT

@login_required(login_url='/login/')
def deposit_view(request):

    methods = PaymentMethod.objects.filter(is_active=True)

    deposits = Deposit.objects.filter(
        user=request.user
    ).order_by('-id')

    if request.method == "POST":
        settings_obj = get_site_settings()

        if not settings_obj.deposits_enabled:

            messages.error(
                request,
                "Deposits are temporarily disabled."
            )

            return redirect('/deposit/')

        amount = Decimal(request.POST.get("amount"))
        method_id = request.POST.get("method")
        proof = request.FILES.get("proof")

        if amount < Decimal("200"):
            messages.error(
                request,
                "Minimum deposit amount is $200."
            )
            return redirect('/deposit/')

        method = PaymentMethod.objects.get(id=method_id)

        Deposit.objects.create(
            user=request.user,
            amount=amount,
            method=method,
            proof=proof
        )

        create_notification(
            user=request.user,
            title="Deposit Submitted",
            message=(
                f"Your deposit request of "
                f"${amount} was submitted "
                f"successfully."
            )
        )

        # LOG
        TransactionLog.objects.create(
            user=request.user,
            tx_type='Deposit',
            amount=amount,
            status='Pending',
            description='Deposit submitted awaiting approval'
        )

        messages.success(
            request,
            "Deposit submitted successfully."
        )

        return redirect('/deposit/')

    return render(
        request,
        'dashboard/deposit.html',
        {
            'methods': methods,
            'deposits': deposits
        }
    )



# WITHDRAW

@login_required(login_url='/login/')
def withdraw_view(request):

    withdrawals = Withdrawal.objects.filter(
        user=request.user
    ).order_by('-id')

    if request.method == "POST":

        settings_obj = get_site_settings()

        if not settings_obj.withdrawals_enabled:

            messages.error(
                request,
                "Withdrawals are temporarily disabled."
            )

            return redirect('/withdraw/')

        amount = Decimal(
            request.POST.get("amount")
        )

        method = request.POST.get("method")

        details = request.POST.get(
            "details"
        )

        pin = request.POST.get("pin")


        # =========================
        # KYC CHECK
        # =========================

        if (
            amount > Decimal("50000")
            and not request.user.kyc_verified
        ):

            messages.error(
                request,
                "KYC verification is required "
                "for withdrawals above $50,000."
            )

            return redirect('/kyc/')


        # =========================
        # PIN EXISTS
        # =========================

        if not request.user.withdrawal_pin:

            messages.error(
                request,
                "Please create a withdrawal PIN "
                "in Account Settings."
            )

            return redirect('/settings/')


        # =========================
        # PIN VALIDATION
        # =========================

        if not check_password(
            pin,
            request.user.withdrawal_pin
        ):

            messages.error(
                request,
                "Invalid withdrawal PIN."
            )

            return redirect('/withdraw/')


        if amount < Decimal("100"):

            messages.error(
                request,
                "Minimum withdrawal is $100."
            )

            return redirect('/withdraw/')


        if amount > request.user.wallet_balance:

            messages.error(
                request,
                "Insufficient wallet balance."
            )

            return redirect('/withdraw/')


        Withdrawal.objects.create(
            user=request.user,
            amount=amount,
            method=method,
            account_details=details
        )

        create_notification(
            user=request.user,
            title="Withdrawal Requested",
            message=(
                f"Your withdrawal request of "
                f"${amount} was submitted."
            )
        )

        # deduct wallet instantly

        request.user.wallet_balance -= amount

        request.user.save()


        # LOG

        TransactionLog.objects.create(
            user=request.user,
            tx_type='Withdrawal',
            amount=amount,
            status='Pending',
            description='Withdrawal request submitted'
        )

        messages.success(
            request,
            "Withdrawal request submitted."
        )

        return redirect('/withdraw/')

    return render(
        request,
        'dashboard/withdraw.html',
        {
            'withdrawals': withdrawals
        }
    )



# REFERRALS

@login_required(login_url='/login/')
def referrals_view(request):

    referrals = request.user.referrals.all().order_by('-date_joined')

    ref_link = request.build_absolute_uri(
        f"/register/?ref={request.user.referral_code}"
    )

    bonus_deposits = Deposit.objects.filter(
        user__referred_by=request.user,
        referral_bonus_paid=True,
        status="Approved"
    ).order_by('-created_at')

    total_earnings = Decimal("0.00")

    for item in bonus_deposits:
        total_earnings += item.amount * Decimal("0.05")

    active_referrals = bonus_deposits.values(
        'user'
    ).distinct().count()

    avg_bonus = (
        total_earnings / active_referrals
        if active_referrals > 0 else 0
    )

    return render(
        request,
        'dashboard/referrals.html',
        {
            'referrals': referrals,
            'ref_link': ref_link,
            'bonus_deposits': bonus_deposits,
            'total_earnings': total_earnings,
            'active_referrals': active_referrals,
            'avg_bonus': avg_bonus,
        }
    )



# INVESTMENTS

@login_required(login_url='/login/')
def investments_view(request):

    plans = InvestmentPlan.objects.filter(
        is_active=True
    )

    my_investments = UserInvestment.objects.filter(
        user=request.user,
        completed=False
    ).order_by('-id')

    
    # CLAIM PROFIT
    
    if request.method == "POST" and request.POST.get("claim_id"):

        inv = UserInvestment.objects.get(
            id=request.POST.get("claim_id"),
            user=request.user
        )

        now = timezone.now()

        passed_days = (now - inv.last_claim).days

        if passed_days < 1:
            messages.error(
                request,
                "Next claim available after 24 hours."
            )
            return redirect('/investments/')

        claim_days = min(passed_days, 3)

        daily_profit = (
            inv.amount *
            inv.plan.daily_roi /
            Decimal("100")
        )

        total_profit = daily_profit * claim_days

        user = request.user
        today = now.date()

        # streak
        if user.last_streak_claim:

            diff = (
                today - user.last_streak_claim
            ).days

            if diff == 1:
                user.claim_streak += 1
            elif diff == 0:
                pass
            else:
                user.claim_streak = 1

        else:
            user.claim_streak = 1

        user.last_streak_claim = today

        # bonus
        bonus = Decimal("0")

        if user.claim_streak % 30 == 0:
            bonus = Decimal("25")

        elif user.claim_streak % 7 == 0:
            bonus = Decimal("5")

        # wallet credit
        user.wallet_balance += total_profit + bonus
        user.save()

        create_notification(
            user=user,
            title="Profit Claimed",
            message=(
                f"You claimed "
                f"${total_profit:.2f} "
                f"profit and "
                f"${bonus:.2f} bonus."
            )
        )

        # LOG PROFIT
        TransactionLog.objects.create(
            user=user,
            tx_type='Profit',
            amount=total_profit,
            status='Success',
            description='Daily profit claimed'
        )

        # LOG BONUS
        if bonus > 0:
            TransactionLog.objects.create(
                user=user,
                tx_type='Bonus',
                amount=bonus,
                status='Success',
                description='Streak bonus earned'
            )

        # update investment
        inv.days_paid += claim_days
        inv.last_claim = now

        if inv.days_paid >= inv.plan.duration_days:

            user.wallet_balance += inv.amount
            user.save()

            inv.completed = True

            # LOG RETURN
            TransactionLog.objects.create(
                user=user,
                tx_type='Return',
                amount=inv.amount,
                status='Success',
                description='Investment capital returned'
            )

        inv.save()

        messages.success(
            request,
            f"${total_profit:.2f} claimed. Bonus: ${bonus:.2f}"
        )

        return redirect('/investments/')

    
    # ACTIVATE PLAN
    
    if request.method == "POST" and request.POST.get("plan_id"):
        settings_obj = get_site_settings()

        if not settings_obj.investments_enabled:

            messages.error(
                request,
                "Investments are temporarily disabled."
            )

            return redirect('/investments/')

        plan = InvestmentPlan.objects.get(
            id=request.POST.get("plan_id")
        )

        amount = Decimal(
            request.POST.get("amount")
        )

        if amount < plan.min_amount:
            messages.error(
                request,
                f"Minimum for {plan.name} is ${plan.min_amount}"
            )
            return redirect('/investments/')

        if amount > plan.max_amount:
            messages.error(
                request,
                f"Maximum for {plan.name} is ${plan.max_amount}"
            )
            return redirect('/investments/')

        if amount > request.user.wallet_balance:
            messages.error(
                request,
                "Insufficient wallet balance."
            )
            return redirect('/investments/')

        request.user.wallet_balance -= amount
        request.user.save()

        UserInvestment.objects.create(
            user=request.user,
            plan=plan,
            amount=amount
        )

        create_notification(
            user=request.user,
            title="Investment Activated",
            message=(
                f"You successfully activated "
                f"{plan.name} with "
                f"${amount}."
            )
        )

        # LOG
        TransactionLog.objects.create(
            user=request.user,
            tx_type='Investment',
            amount=amount,
            status='Success',
            description=f'{plan.name} plan activated'
        )

        messages.success(
            request,
            "Investment activated successfully."
        )

        return redirect('/investments/')

    return render(
        request,
        'dashboard/investments.html',
        {
            'plans': plans,
            'my_investments': my_investments
        }
    )



# TRANSACTIONS

@login_required(login_url='/login/')
def transactions_view(request):

    logs = TransactionLog.objects.filter(
        user=request.user
    ).order_by('-id')

    return render(
        request,
        'dashboard/transactions.html',
        {
            'logs': logs
        }
    )


from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal

from .models import (
    Deposit,
    Withdrawal,
    UserInvestment
)

from django.contrib.auth import get_user_model
User = get_user_model()


@superuser_required
def owner_dashboard_view(request):

    today = timezone.now().date()

    
    # USERS
    
    total_users = User.objects.count()
    verified_users = User.objects.filter(
        is_verified=True
    ).count()

    new_users_today = User.objects.filter(
        date_joined__date=today
    ).count()

    
    # DEPOSITS
    
    total_deposits = Deposit.objects.filter(
        status="Approved"
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0")

    pending_deposits = Deposit.objects.filter(
        status="Pending"
    ).count()

    deposits_today = Deposit.objects.filter(
        status="Approved",
        created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0")

    
    # WITHDRAWALS
    
    total_withdrawals = Withdrawal.objects.filter(
        status="Approved"
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0")

    pending_withdrawals = Withdrawal.objects.filter(
        status="Pending"
    ).count()

    withdrawals_today = Withdrawal.objects.filter(
        status="Approved",
        created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0")

    
    # INVESTMENTS
    
    active_investments = UserInvestment.objects.filter(
        completed=False
    ).count()

    total_invested = UserInvestment.objects.aggregate(
        total=Sum('amount')
    )['total'] or Decimal("0")

    
    # WALLET LIABILITY
    
    total_wallet_balance = User.objects.aggregate(
        total=Sum('wallet_balance')
    )['total'] or Decimal("2")

    pending_kyc = KYCSubmission.objects.filter(
        status="Pending"
    ).count()

    approved_kyc = KYCSubmission.objects.filter(
        status="Approved"
    ).count()

    rejected_kyc = KYCSubmission.objects.filter(
        status="Rejected"
    ).count()

    
    # RECENT ACTIVITY
    
    recent_deposits = Deposit.objects.order_by(
        '-id'
    )[:5]

    recent_withdrawals = Withdrawal.objects.order_by(
        '-id'
    )[:5]

    context = {
        # users
        'total_users': total_users,
        'verified_users': verified_users,
        'new_users_today': new_users_today,

        # deposits
        'total_deposits': total_deposits,
        'pending_deposits': pending_deposits,
        'deposits_today': deposits_today,

        # withdrawals
        'total_withdrawals': total_withdrawals,
        'pending_withdrawals': pending_withdrawals,
        'withdrawals_today': withdrawals_today,

        # investments
        'active_investments': active_investments,
        'total_invested': total_invested,

        # wallet
        'total_wallet_balance': total_wallet_balance,

        # recent
        'recent_deposits': recent_deposits,
        'recent_withdrawals': recent_withdrawals,

        #kyc
        'pending_kyc': pending_kyc,
        'approved_kyc': approved_kyc,
        'rejected_kyc': rejected_kyc,
    }

    return render(
        request,
        'owner/dashboard.html',
        context
    )


# OWNER ANALYTICS

@login_required(login_url='/login/')
def owner_analytics_view(request):

    if not request.user.is_superuser:
        return redirect('/dashboard/')


    
    # USER ANALYTICS
    

    total_users = User.objects.count()

    verified_users = User.objects.filter(
        is_verified=True
    ).count()

    suspended_users = User.objects.filter(
        is_suspended=True
    ).count()

    active_users = total_users - suspended_users

    today = timezone.now().date()

    new_users_today = User.objects.filter(
        date_joined__date=today
    ).count()


    
    # DEPOSITS
    

    total_deposits = Deposit.objects.filter(
        status="Approved"
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    deposits_today = Deposit.objects.filter(
        status="Approved",
        created_at__date=today
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    pending_deposits = Deposit.objects.filter(
        status="Pending"
    ).count()


    
    # WITHDRAWALS
    

    total_withdrawals = Withdrawal.objects.filter(
        status="Approved"
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    withdrawals_today = Withdrawal.objects.filter(
        status="Approved",
        created_at__date=today
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    pending_withdrawals = Withdrawal.objects.filter(
        status="Pending"
    ).count()


    
    # INVESTMENTS
    

    total_invested = UserInvestment.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    active_investments = UserInvestment.objects.filter(
        completed=False
    ).count()


    
    # REFERRALS
    

    referred_users = User.objects.filter(
        referred_by__isnull=False
    ).count()


    
    # TOP INVESTORS
    

    top_investors = UserInvestment.objects.values(
        'user__username'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]


    return render(
        request,
        'owner/analytics.html',
        {
            'total_users': total_users,
            'verified_users': verified_users,
            'suspended_users': suspended_users,
            'active_users': active_users,
            'new_users_today': new_users_today,

            'total_deposits': total_deposits,
            'deposits_today': deposits_today,
            'pending_deposits': pending_deposits,

            'total_withdrawals': total_withdrawals,
            'withdrawals_today': withdrawals_today,
            'pending_withdrawals': pending_withdrawals,

            'total_invested': total_invested,
            'active_investments': active_investments,

            'referred_users': referred_users,

            'top_investors': top_investors,
        }
    )



# FINANCE PANEL

@login_required(login_url='/login/')
def finance_panel_view(request):

    if not request.user.is_superuser:
        return redirect('/dashboard/')


    
    # TOTAL DEPOSITS
    

    total_deposits = Deposit.objects.filter(
        status="Approved"
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0


    
    # TOTAL WITHDRAWALS
    

    total_withdrawals = Withdrawal.objects.filter(
        status="Approved"
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0


    
    # NET PLATFORM BALANCE
    

    net_balance = (
        total_deposits - total_withdrawals
    )


    
    # TOTAL INVESTED
    

    total_invested = UserInvestment.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0


    
    # ACTIVE INVESTMENTS
    

    active_investments = UserInvestment.objects.filter(
        completed=False
    ).count()


    
    # WALLET LIABILITY
    

    total_wallet_liability = User.objects.aggregate(
        total=Sum('wallet_balance')
    )['total'] or 0


    
    # PENDING QUEUES
    

    pending_deposits = Deposit.objects.filter(
        status="Pending"
    ).count()

    pending_withdrawals = Withdrawal.objects.filter(
        status="Pending"
    ).count()


    
    # TOTAL PROFITS PAID
    

    total_profit_paid = Decimal("0")

    logs = TransactionLog.objects.filter(
    tx_type="Profit Claim"
    )

    for log in logs:
        total_profit_paid += log.amount


    
    # REFERRAL BONUSES
    

    total_referral_bonus = Decimal("0")

    bonus_deposits = Deposit.objects.filter(
        referral_bonus_paid=True
    )

    for dep in bonus_deposits:
        total_referral_bonus += (
            dep.amount * Decimal("0.05")
        )


    
    # RESERVE ESTIMATE
    

    reserve_estimate = (
        net_balance -
        total_wallet_liability
    )


    
    # RECENT PENDING
    

    recent_pending_deposits = Deposit.objects.filter(
        status="Pending"
    ).order_by('-id')[:5]

    recent_pending_withdrawals = Withdrawal.objects.filter(
        status="Pending"
    ).order_by('-id')[:5]


    return render(
        request,
        'owner/finance.html',
        {
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'net_balance': net_balance,
            'total_invested': total_invested,
            'active_investments': active_investments,
            'total_wallet_liability':
            total_wallet_liability,
            'pending_deposits':
            pending_deposits,
            'pending_withdrawals':
            pending_withdrawals,
            'total_profit_paid':
            total_profit_paid,
            'total_referral_bonus':
            total_referral_bonus,
            'reserve_estimate':
            reserve_estimate,

            'recent_pending_deposits':
            recent_pending_deposits,

            'recent_pending_withdrawals':
            recent_pending_withdrawals,
        }
    )


@superuser_required
def users_management_view(request):

    search = request.GET.get('search')

    users = User.objects.all().order_by('-id')

    if search:
        users = users.filter(
            username__icontains=search
        )

    return render(
        request,
        'owner/users.html',
        {
            'users': users
        }
    )


@superuser_required
def user_detail_view(request, user_id):

    user_obj = User.objects.get(id=user_id)

    deposits = Deposit.objects.filter(
        user=user_obj
    ).order_by('-id')[:5]

    withdrawals = Withdrawal.objects.filter(
        user=user_obj
    ).order_by('-id')[:5]

    investments = UserInvestment.objects.filter(
        user=user_obj
    ).order_by('-id')[:5]

    
    # WALLET ACTIONS
    
    if request.method == "POST":

        action = request.POST.get('action')

        amount = Decimal(
            request.POST.get('amount', 0)
        )

        note = request.POST.get('note')

        # CREDIT
        if action == "credit":

            user_obj.wallet_balance += amount
            user_obj.save()

            TransactionLog.objects.create(
                user=user_obj,
                transaction_type="Bonus",
                amount=amount,
                status="Approved",
                description=f"Admin Credit: {note}"
            )

            messages.success(
                request,
                "Wallet credited successfully."
            )

        # DEDUCT
        elif action == "deduct":

            if amount > user_obj.wallet_balance:

                messages.error(
                    request,
                    "Insufficient user balance."
                )

                return redirect(
                    f'/owner-user/{user_id}/'
                )

            user_obj.wallet_balance -= amount
            user_obj.save()

            TransactionLog.objects.create(
                user=user_obj,
                transaction_type="Penalty",
                amount=amount,
                status="Approved",
                description=f"Admin Deduction: {note}"
            )

            messages.success(
                request,
                "Wallet deducted successfully."
            )

        # SUSPEND
        elif action == "suspend":

            user_obj.is_suspended = True
            user_obj.suspension_reason = note
            user_obj.save()

            messages.success(
                request,
                "User suspended."
            )

        # ACTIVATE
        elif action == "activate":

            user_obj.is_suspended = False
            user_obj.suspension_reason = ""
            user_obj.save()

            messages.success(
                request,
                "User activated."
            )

        return redirect(
            f'/owner-user/{user_id}/'
        )

    return render(
        request,
        'owner/user_detail.html',
        {
            'user_obj': user_obj,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'investments': investments,
        }
    )

@login_required(login_url='/login/')
def owner_user_detail_view(request, user_id):

    if not request.user.is_superuser:
        return redirect('/dashboard/')

    User = get_user_model()

    user_obj = User.objects.get(id=user_id)

    deposits = Deposit.objects.filter(
        user=user_obj
    ).order_by('-id')

    withdrawals = Withdrawal.objects.filter(
        user=user_obj
    ).order_by('-id')

    investments = UserInvestment.objects.filter(
        user=user_obj
    ).order_by('-id')

    referrals = User.objects.filter(
        referred_by=user_obj
    )

    total_referral_earnings = Decimal("0")

    referral_deposits = Deposit.objects.filter(
        user__referred_by=user_obj,
        referral_bonus_paid=True,
        status="Approved"
    )

    for dep in referral_deposits:
        total_referral_earnings += (
            dep.amount * Decimal("0.05")
        )



    
    # SUSPEND USER
    

    if request.method == "POST" and request.POST.get("action") == "suspend":

        user_obj.is_suspended = True
        user_obj.save()

        # OWNER LOG
        create_owner_log(
            owner=request.user,
            action="User Suspended",
            description=f"Suspended {user_obj.username}",
            target_user=user_obj
        )

        messages.success(
            request,
            "User suspended successfully."
        )

        return redirect(f'/owner-user/{user_obj.id}/')



    
    # ACTIVATE USER
    

    if request.method == "POST" and request.POST.get("action") == "activate":

        user_obj.is_suspended = False
        user_obj.save()

        # OWNER LOG
        create_owner_log(
            owner=request.user,
            action="User Activated",
            description=f"Activated {user_obj.username}",
            target_user=user_obj
        )

        messages.success(
            request,
            "User activated successfully."
        )

        return redirect(f'/owner-user/{user_obj.id}/')



    
    # EDIT BALANCE
    

    if request.method == "POST" and request.POST.get("action") == "balance":

        old_balance = user_obj.wallet_balance

        new_balance = Decimal(
            request.POST.get("balance")
        )

        user_obj.wallet_balance = new_balance
        user_obj.save()

        # OWNER LOG
        create_owner_log(
            owner=request.user,
            action="Balance Edited",
            description=(
                f"{user_obj.username} balance changed "
                f"from ${old_balance} to ${new_balance}"
            ),
            target_user=user_obj
        )

        messages.success(
            request,
            "Wallet balance updated."
        )

        return redirect(f'/owner-user/{user_obj.id}/')



    if (
        request.method == "POST"
        and request.POST.get("action")
        == "reset_pin"
    ):

        user_obj.withdrawal_pin = None

        user_obj.save()

        create_owner_log(
            owner=request.user,
            action="Withdrawal PIN Reset",
            description=user_obj.username
        )

        Notification.objects.create(
            user=user_obj,
            title="Withdrawal PIN Reset",
            message=(
                "Your withdrawal PIN was reset. "
                "Please create a new PIN."
            )
        )

        messages.success(
            request,
            "Withdrawal PIN reset successfully."
        )

        return redirect(
            f'/owner-user/{user_obj.id}/'
        )



    return render(
        request,
        'owner/user_detail.html',
        {
            'user_obj': user_obj,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'investments': investments,
            'referrals': referrals,
            'total_referral_earnings':
            total_referral_earnings,
        }
    )


@login_required(login_url='/login/')
def future_admin_tools_view(request):

    if not request.user.is_superuser:
        return redirect('/dashboard/')


    settings_obj = get_site_settings()


    
    # SAVE CONTROLS
    

    if request.method == "POST":

        old_maintenance = settings_obj.maintenance_mode
        old_deposits = settings_obj.deposits_enabled
        old_withdrawals = settings_obj.withdrawals_enabled
        old_investments = settings_obj.investments_enabled
        old_announcement = settings_obj.site_announcement


        settings_obj.maintenance_mode = (
            request.POST.get("maintenance_mode")
            == "on"
        )

        settings_obj.deposits_enabled = (
            request.POST.get("deposits_enabled")
            == "on"
        )

        settings_obj.withdrawals_enabled = (
            request.POST.get("withdrawals_enabled")
            == "on"
        )

        settings_obj.investments_enabled = (
            request.POST.get("investments_enabled")
            == "on"
        )

        settings_obj.site_announcement = (
            request.POST.get("site_announcement")
        )

        settings_obj.save()


        
        # OWNER ACTION LOG
        

        create_owner_log(
            owner=request.user,
            action="Platform Settings Updated",
            description=(
                f"Maintenance: "
                f"{old_maintenance} → "
                f"{settings_obj.maintenance_mode}, "

                f"Deposits: "
                f"{old_deposits} → "
                f"{settings_obj.deposits_enabled}, "

                f"Withdrawals: "
                f"{old_withdrawals} → "
                f"{settings_obj.withdrawals_enabled}, "

                f"Investments: "
                f"{old_investments} → "
                f"{settings_obj.investments_enabled}"
            )
        )

        # Announcement log
        if old_announcement != settings_obj.site_announcement:

            create_owner_log(
                owner=request.user,
                action="Announcement Updated",
                description=(
                    "Updated global site announcement"
                )
            )


        messages.success(
            request,
            "Platform settings updated."
        )

        return redirect('/future-admin-tools/')


    return render(
        request,
        'owner/future_tools.html',
        {
            'settings_obj': settings_obj
        }
    )


def maintenance_view(request):

    return render(
        request,
        'maintenance.html'
    )


@login_required(login_url='/login/')
def broadcast_message_view(request):

    if not request.user.is_superuser:
        return redirect('/dashboard/')


    if request.method == "POST":

        title = request.POST.get("title")
        message_text = request.POST.get("message")

        users = User.objects.all()

        notifications = []

        for user in users:

            notifications.append(

                Notification(
                    user=user,
                    title=title,
                    message=message_text
                )

            )

        Notification.objects.bulk_create(
            notifications
        )

        messages.success(
            request,
            "Broadcast sent successfully."
        )

        return redirect('/broadcast-message/')


    return render(
        request,
        'owner/broadcast.html'
    )


@login_required(login_url='/login/')
def notifications_view(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-id')

    return render(
        request,
        'dashboard/notifications.html',
        {
            'notifications': notifications
        }
    )


@login_required(login_url='/login/')
def read_notification_view(request, notification_id):

    notification = Notification.objects.get(
        id=notification_id,
        user=request.user
    )

    notification.is_read = True
    notification.save()

    return redirect('/notifications/')


@login_required(login_url='/login/')
def read_all_notifications_view(request):

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return redirect('/notifications/')


@login_required(login_url='/login/')
def owner_action_logs_view(request):

    if not request.user.is_superuser:
        return redirect('/dashboard/')

    logs = OwnerActionLog.objects.all().order_by(
        '-id'
    )

    return render(
        request,
        'owner/action_logs.html',
        {
            'logs': logs
        }
    )


@login_required(login_url='/login/')
def owner_broadcasts_view(request):

    if not request.user.is_superuser:
        return redirect('/dashboard/')

    broadcasts = BroadcastMessage.objects.all().order_by(
        '-is_pinned',
        '-id'
    )

    if request.method == "POST":

        
        # DELETE BROADCAST
        

        if request.POST.get("action") == "delete":

            broadcast = get_object_or_404(
                BroadcastMessage,
                id=request.POST.get("broadcast_id")
            )

            create_owner_log(
                owner=request.user,
                action="Broadcast Deleted",
                description=(
                    f"Deleted broadcast: "
                    f"{broadcast.title}"
                )
            )

            broadcast.delete()

            messages.success(
                request,
                "Broadcast deleted successfully."
            )

            return redirect('/owner-broadcasts/')


        
        # CREATE BROADCAST
        

        title = request.POST.get("title")
        message = request.POST.get("message")
        priority = request.POST.get("priority")
        audience = request.POST.get("audience")

        pinned = (
            request.POST.get("pinned")
            == "on"
        )

        BroadcastMessage.objects.create(
            title=title,
            message=message,
            priority=priority,
            target_audience=audience,
            is_pinned=pinned
        )

        create_owner_log(
            owner=request.user,
            action="Broadcast Created",
            description=(
                f"Created {priority} broadcast: "
                f"{title}"
            )
        )

        messages.success(
            request,
            "Broadcast created successfully."
        )

        return redirect('/owner-broadcasts/')


    return render(
        request,
        'owner/broadcasts.html',
        {
            'broadcasts': broadcasts
        }
    )


def create_security_log(
    user,
    action,
    details=""
):

    SecurityLog.objects.create(
        user=user,
        action=action,
        details=details
    )



@login_required(login_url='/login/')
def settings_view(request):

    logs = SecurityLog.objects.filter(
        user=request.user
    ).order_by('-id')[:20]


    
    # CHANGE EMAIL
    

    if (
        request.method == "POST"
        and request.POST.get("action")
        == "change_email"
    ):

        new_email = request.POST.get(
            "new_email"
        )

        code = str(
            random.randint(
                100000,
                999999
            )
        )

        request.session[
            "email_change_code"
        ] = code

        request.session[
            "new_email"
        ] = new_email

        request.session[
            "email_change_time"
        ] = timezone.now().timestamp()

        send_mail(
            "OneMarketX Email Change Verification",
            f"Verification code: {code}",
            None,
            [new_email]
        )

        create_security_log(
            request.user,
            "Email Change Requested",
            f"New Email: {new_email}"
        )

        messages.success(
            request,
            "Verification code sent."
        )

        return redirect(
            '/verify-email-change/'
        )


    
    # CHANGE PASSWORD
    

    if (
        request.method == "POST"
        and request.POST.get("action")
        == "change_password"
    ):

        password1 = request.POST.get(
            "password1"
        )

        password2 = request.POST.get(
            "password2"
        )

        if password1 != password2:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect(
                '/settings/'
            )

        code = str(
            random.randint(
                100000,
                999999
            )
        )

        request.session[
            "password_change_code"
        ] = code

        request.session[
            "new_password"
        ] = password1

        request.session[
            "password_change_time"
        ] = timezone.now().timestamp()

        send_mail(
            "OneMarketX Password Change Verification",
            f"Verification code: {code}",
            None,
            [request.user.email]
        )

        create_security_log(
            request.user,
            "Password Change Requested"
        )

        messages.success(
            request,
            "Verification code sent."
        )

        return redirect(
            '/verify-password-change/'
        )


    if (
        request.method == "POST"
        and request.POST.get("action")
        == "set_withdrawal_pin"
    ):

        if request.user.withdrawal_pin:

            messages.error(
                request,
                "Withdrawal PIN already exists. Contact support if you need it reset."
            )

            return redirect('/settings/')

        pin = request.POST.get("pin")

        confirm_pin = request.POST.get(
            "confirm_pin"
        )

        if pin != confirm_pin:

            messages.error(
                request,
                "PINs do not match."
            )

            return redirect('/settings/')

        if (
            not pin.isdigit()
            or len(pin) != 4
        ):

            messages.error(
                request,
                "PIN must be exactly 4 digits."
            )

            return redirect('/settings/')

        request.user.withdrawal_pin = (
            make_password(pin)
        )

        request.user.save()

        create_security_log(
            request.user,
            "Withdrawal PIN Created"
        )

        messages.success(
            request,
            "Withdrawal PIN created successfully."
        )

        return redirect('/settings/')


    return render(
        request,
        'dashboard/settings.html',
        {
            'logs': logs
        }
    )


@login_required(login_url='/login/')
def verify_email_change_view(request):

    if request.method == "POST":

        code = request.POST.get("code")

        stored_code = request.session.get(
            "email_change_code"
        )

        sent_time = request.session.get(
            "email_change_time"
        )

        if not stored_code:

            messages.error(
                request,
                "No active verification request."
            )

            return redirect('/settings/')

        if (
            timezone.now().timestamp()
            - sent_time
        ) > 600:

            messages.error(
                request,
                "Verification code expired."
            )

            return redirect(
                '/verify-email-change/'
            )

        if code == stored_code:

            request.user.email = (
                request.session.get(
                    "new_email"
                )
            )

            request.user.last_email_change = (
                timezone.now()
            )

            request.user.save()

            create_security_log(
                request.user,
                "Email Changed"
            )

            request.session.pop(
                "email_change_code",
                None
            )

            request.session.pop(
                "new_email",
                None
            )

            request.session.pop(
                "email_change_time",
                None
            )

            messages.success(
                request,
                "Email updated."
            )

            return redirect('/settings/')

        messages.error(
            request,
            "Invalid verification code."
        )

    return render(
        request,
        'dashboard/verify_email_change.html'
    )


@login_required(login_url='/login/')
def verify_password_change_view(request):

    if request.method == "POST":

        code = request.POST.get("code")

        stored_code = request.session.get(
            "password_change_code"
        )

        sent_time = request.session.get(
            "password_change_time"
        )

        if not stored_code:

            messages.error(
                request,
                "No active verification request."
            )

            return redirect('/settings/')

        if (
            timezone.now().timestamp()
            - sent_time
        ) > 600:

            messages.error(
                request,
                "Verification code expired."
            )

            return redirect(
                '/verify-password-change/'
            )

        if code == stored_code:

            request.user.set_password(
                request.session.get(
                    "new_password"
                )
            )

            request.user.last_password_change = (
                timezone.now()
            )

            request.user.save()

            create_security_log(
                request.user,
                "Password Changed"
            )

            request.session.pop(
                "password_change_code",
                None
            )

            request.session.pop(
                "new_password",
                None
            )

            request.session.pop(
                "password_change_time",
                None
            )

            messages.success(
                request,
                "Password updated."
            )

            return redirect('/login/')

        messages.error(
            request,
            "Invalid verification code."
        )

    return render(
        request,
        'dashboard/verify_password_change.html'
    )

@login_required(login_url='/login/')
def resend_email_change_code(request):

    last_sent = request.session.get(
        "email_change_time"
    )

    if last_sent:

        if (
            timezone.now().timestamp()
            - last_sent
        ) < 30:

            messages.error(
                request,
                "Please wait 30 seconds."
            )

            return redirect(
                '/verify-email-change/'
            )

    code = str(
        random.randint(
            100000,
            999999
        )
    )

    request.session[
        "email_change_code"
    ] = code

    request.session[
        "email_change_time"
    ] = timezone.now().timestamp()

    send_mail(
        "OneMarketX Email Change Verification",
        f"Verification code: {code}",
        None,
        [
            request.session.get(
                "new_email"
            )
        ]
    )

    messages.success(
        request,
        "New code sent."
    )

    return redirect(
        '/verify-email-change/'
    )

@login_required(login_url='/login/')
def resend_password_change_code(request):

    last_sent = request.session.get(
        "password_change_time"
    )

    if last_sent:

        if (
            timezone.now().timestamp()
            - last_sent
        ) < 30:

            messages.error(
                request,
                "Please wait 30 seconds."
            )

            return redirect(
                '/verify-password-change/'
            )

    code = str(
        random.randint(
            100000,
            999999
        )
    )

    request.session[
        "password_change_code"
    ] = code

    request.session[
        "password_change_time"
    ] = timezone.now().timestamp()

    send_mail(
        "OneMarketX Password Change Verification",
        f"Verification code: {code}",
        None,
        [request.user.email]
    )

    messages.success(
        request,
        "New code sent."
    )

    return redirect(
        '/verify-password-change/'
    )

from .models import KYCSubmission


@login_required(login_url='/login/')
def kyc_view(request):

    kyc = KYCSubmission.objects.filter(
        user=request.user
    ).first()

    
    # NEW SUBMISSION
    

    if request.method == "POST":

        # APPROVED USERS CANNOT RESUBMIT

        if kyc and kyc.status == "Approved":

            messages.error(
                request,
                "Your KYC has already been approved."
            )

            return redirect('/kyc/')

        # REJECTED USERS CAN RESUBMIT

        if kyc and kyc.status == "Rejected":

            kyc.id_document = request.FILES.get(
                "id_document"
            )

            kyc.selfie = request.FILES.get(
                "selfie"
            )

            kyc.address_proof = request.FILES.get(
                "address_proof"
            )

            kyc.status = "Pending"

            kyc.admin_note = ""

            kyc.reviewed_at = None

            kyc.save()

            create_security_log(
                request.user,
                "KYC Resubmitted"
            )

            Notification.objects.create(
                user=request.user,
                title="KYC Resubmitted",
                message=(
                    "Your updated KYC documents "
                    "have been submitted for review."
                )
            )

            messages.success(
                request,
                "KYC resubmitted successfully."
            )

            return redirect('/kyc/')

        # PENDING USERS CANNOT RESUBMIT

        if kyc and kyc.status == "Pending":

            messages.error(
                request,
                "Your KYC is currently under review."
            )

            return redirect('/kyc/')

        # FIRST-TIME SUBMISSION

        if not kyc:

            kyc = KYCSubmission.objects.create(
                user=request.user,
                id_document=request.FILES.get(
                    "id_document"
                ),
                selfie=request.FILES.get(
                    "selfie"
                ),
                address_proof=request.FILES.get(
                    "address_proof"
                )
            )

            create_security_log(
                request.user,
                "KYC Submitted"
            )

            Notification.objects.create(
                user=request.user,
                title="KYC Submitted",
                message=(
                    "Your KYC documents "
                    "are under review."
                )
            )

            messages.success(
                request,
                "KYC submitted successfully."
            )

            return redirect('/kyc/')

    return render(
        request,
        'dashboard/kyc.html',
        {
            'kyc': kyc
        }
    )

@login_required(login_url='/login/')
def owner_kyc_view(request):

    if not request.user.is_superuser:
        return redirect('/dashboard/')

    submissions = KYCSubmission.objects.all().order_by(
        '-submitted_at'
    )

    return render(
        request,
        'owner/kyc.html',
        {
            'submissions': submissions
        }
    )

@login_required(login_url='/login/')
def owner_kyc_detail_view(
    request,
    kyc_id
):

    if not request.user.is_superuser:
        return redirect('/dashboard/')

    kyc = get_object_or_404(
        KYCSubmission,
        id=kyc_id
    )

    if request.method == "POST":

        action = request.POST.get(
            "action"
        )

        note = request.POST.get(
            "note"
        )

        kyc.admin_note = note
        kyc.reviewed_at = timezone.now()

        if action == "approve":

            kyc.status = "Approved"

            kyc.user.kyc_verified = True
            kyc.user.save()

            Notification.objects.create(
                user=kyc.user,
                title="KYC Approved",
                message=(
                    "Your KYC has been approved."
                )
            )

        elif action == "reject":

            kyc.status = "Rejected"

            kyc.user.kyc_verified = False
            kyc.user.save()

            Notification.objects.create(
                user=kyc.user,
                title="KYC Rejected",
                message=(
                    "Your KYC was rejected."
                )
            )

        kyc.save()

        create_owner_log(
            owner=request.user,
            action=f"KYC {kyc.status}",
            description=(
                f"{kyc.user.username}"
            )
        )

        messages.success(
            request,
            "KYC updated."
        )

        return redirect(
            f'/owner-kyc/{kyc.id}/'
        )

    return render(
        request,
        'owner/kyc_detail.html',
        {
            'kyc': kyc
        }
    )