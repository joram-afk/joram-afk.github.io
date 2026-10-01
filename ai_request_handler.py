from __future__ import annotations

import asyncio
from typing import Any

from ai import invoke_ai
from config import settings
from database import get_connection
from models import utc_now
from payment import get_payment_status, initiate_stk_push
from payment_approval import PaymentApprovalWorkflow


class AIRequestHandler:
    """Handles AI requests with user-approved M-Pesa payments."""

    def __init__(self):
        self.approval_workflow = PaymentApprovalWorkflow()

    async def process_with_approval(self, user_id: int, prompt: str, service_type: str, phone_number: str) -> dict[str, Any]:
        """
        Process AI request with user approval for payment.
        User must explicitly approve before STK push is sent.
        """
        # Step 1: Validate request
        amount = settings.SERVICE_PRICING.get(service_type, 0)
        valid, reason = self.approval_workflow.validate_request(amount, service_type)
        if not valid:
            return {"success": False, "error": reason}

        # Step 2: Get user approval
        if self.approval_workflow.requires_user_approval(amount):
            approved = self.approval_workflow.get_user_approval(amount, service_type, phone_number)
            if not approved:
                return {"success": False, "error": "Payment not approved by user"}

        # Step 3: Initiate M-Pesa STK push
        print("\n📱 Sending M-Pesa prompt to your phone...")
        try:
            payment = await initiate_stk_push(user_id, phone_number, service_type)
        except Exception as e:
            return {"success": False, "error": f"Failed to send M-Pesa prompt: {str(e)}"}

        # Step 4: Wait for payment confirmation
        print("⏳ Waiting for payment confirmation (max 30 seconds)...")
        print("   Check your phone and enter your M-Pesa PIN\n")
        confirmed = await self._wait_for_payment_confirmation(payment.checkout_request_id, max_wait=30)

        if not confirmed:
            return {"success": False, "error": "Payment timeout - you did not confirm the M-Pesa prompt"}

        print("✅ Payment confirmed!")

        # Step 5: Call Claude AI
        print("🤖 Processing your request with AI...")
        try:
            transaction = await invoke_ai(user_id, payment.checkout_request_id, prompt, service_type)
        except Exception as e:
            return {"success": False, "error": f"AI processing failed: {str(e)}"}

        return {
            "success": True,
            "payment_id": payment.checkout_request_id,
            "response": transaction.answer,
            "cost": amount,
        }

    async def _wait_for_payment_confirmation(self, checkout_id: str, max_wait: int = 30) -> bool:
        """Poll for M-Pesa payment confirmation."""
        poll_interval = 2  # seconds
        max_attempts = max_wait // poll_interval

        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            payment = get_payment_status(checkout_id)

            if payment and payment.status == "paid":
                return True

            remaining = max_wait - (attempt + 1) * poll_interval
            if remaining > 0 and remaining % 10 == 0:
                print(f"   Still waiting... ({remaining}s remaining)")

        return False
