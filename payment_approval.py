from __future__ import annotations

from typing import Any

from config import settings
from models import utc_now


class PaymentApprovalWorkflow:
    """Handles user approval for payments before execution."""

    def __init__(self, approval_policy: dict[str, Any] | None = None):
        self.policy = approval_policy or self._default_policy()

    @staticmethod
    def _default_policy() -> dict[str, Any]:
        return {
            "maxTransactionAmount": 5000,
            "maxDailyAmount": 20000,
            "requireApprovalAbove": 100,
            "allowedServices": [
                "basicQuery",
                "advancedAnalysis",
                "customReport",
                "premiumSupport",
            ],
        }

    def validate_request(self, amount: int, service_type: str) -> tuple[bool, str]:
        """Validate payment request against policy."""
        if service_type not in self.policy["allowedServices"]:
            return False, f"Service type '{service_type}' not allowed"

        if amount > self.policy["maxTransactionAmount"]:
            return False, f"Amount {amount} KES exceeds max transaction limit {self.policy['maxTransactionAmount']} KES"

        return True, "Valid"

    def requires_user_approval(self, amount: int) -> bool:
        """Check if user approval is required."""
        return amount >= self.policy["requireApprovalAbove"]

    def format_approval_prompt(self, amount: int, service_type: str, phone_number: str) -> str:
        """Format the user approval prompt."""
        return f"""
╔════════════════════════════════════╗
║  PAYMENT APPROVAL REQUIRED          ║
╚════════════════════════════════════╝

Service:    {service_type}
Cost:       {amount} KES
Phone:      {phone_number}

⚠️  You will receive an M-Pesa prompt on your phone.
    Enter your M-Pesa PIN to confirm payment.

Approve payment? [y/N]: """

    def get_user_approval(self, amount: int, service_type: str, phone_number: str) -> bool:
        """Get explicit user approval via CLI."""
        prompt = self.format_approval_prompt(amount, service_type, phone_number)
        response = input(prompt).strip().lower()
        return response == "y"
