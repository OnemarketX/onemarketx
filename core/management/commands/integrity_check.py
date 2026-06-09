from django.core.management.base import BaseCommand
from decimal import Decimal

from core.models import (
    Deposit,
    Withdrawal,
    UserInvestment,
    TransactionLog
)


class Command(BaseCommand):

    help = "Run OneMarketX data integrity scan"

    def handle(self, *args, **kwargs):

        self.stdout.write("")
        self.stdout.write("=== DATA INTEGRITY REPORT ===")

        issues = 0

        
        # DEPOSITS
        
        deposits = Deposit.objects.all()

        for d in deposits:

            if d.status == "Approved" and not d.credited:
                issues += 1
                self.stdout.write(
                    f"[Deposit BUG] Approved not credited: #{d.id}"
                )

            if d.status != "Approved" and d.credited:
                issues += 1
                self.stdout.write(
                    f"[Deposit BUG] Credited but not approved: #{d.id}"
                )

        
        # WITHDRAWALS
        
        withdrawals = Withdrawal.objects.all()

        for w in withdrawals:

            if w.status == "Approved" and not w.deducted:
                issues += 1
                self.stdout.write(
                    f"[Withdraw BUG] Approved not deducted: #{w.id}"
                )

            if w.status == "Rejected" and w.deducted:
                issues += 1
                self.stdout.write(
                    f"[Withdraw BUG] Rejected but deducted: #{w.id}"
                )

        
        # INVESTMENTS
        
        investments = UserInvestment.objects.all()

        for inv in investments:

            if inv.days_paid > inv.plan.duration_days:
                issues += 1
                self.stdout.write(
                    f"[Investment BUG] Overpaid days: #{inv.id}"
                )

            if inv.completed and inv.days_paid < inv.plan.duration_days:
                issues += 1
                self.stdout.write(
                    f"[Investment BUG] Completed too early: #{inv.id}"
                )

        
        # WALLET NEGATIVE
        
        from django.contrib.auth import get_user_model

        User = get_user_model()

        users = User.objects.all()

        for user in users:

            if user.wallet_balance < Decimal("0"):
                issues += 1
                self.stdout.write(
                    f"[Wallet BUG] Negative balance: {user.username}"
                )

        
        # TRANSACTION LOGS
        
        if TransactionLog.objects.count() == 0:
            issues += 1
            self.stdout.write(
                "[Log Warning] No transaction logs found"
            )

        
        # RESULT
        
        self.stdout.write("")

        if issues == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "✔ No integrity issues found."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ {issues} issues detected."
                )
            )