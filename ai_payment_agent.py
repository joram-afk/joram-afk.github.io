from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timezone
from typing import Any

import httpx
from anthropic import AsyncAnthropic

from config import settings
from database import get_connection
from models import Transaction, utc_now


class AIPaymentAgent:
    """AI Agent that can execute payments on behalf of users."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def analyze_and_pay(self, user_id: int, prompt: str, service_type: str) -> dict[str, Any]:
        """
        AI analyzes the user's request and autonomously executes payment if needed.
        Returns: {success, payment_id, response, cost}
        """
        # Step 1: Get user info
        conn = get_connection()
        try:
            user = conn.execute(
                "SELECT email, phone_number FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        finally:
            conn.close()

        if not user:
            return {"success": False, "error": "User not found"}

        phone_number = user["phone_number"]
        if not phone_number:
            return {"success": False, "error": "No phone number on file"}

        # Step 2: AI decides if payment is needed
        decision = await self._get_ai_decision(prompt, service_type)
        if not decision["should_pay"]:
            return {
                "success": False,
                "error": decision.get("reason", "AI determined payment not needed"),
            }

        # Step 3: Check user balance
        balance = await self._check_mpesa_balance(phone_number)
        amount = settings.SERVICE_PRICING[service_type]
        if balance < amount:
            return {
                "success": False,
                "error": f"Insufficient balance. Required: {amount} KES, Available: {balance} KES",
            }

        # Step 4: Execute payment
        payment = await self._execute_autonomous_payment(user_id, phone_number, amount, service_type)
        if not payment["success"]:
            return payment

        # Step 5: Wait for payment confirmation
        confirmed = await self._wait_for_payment(payment["checkout_id"], max_wait=30)
        if not confirmed:
            return {
                "success": False,
                "error": "Payment timeout - user did not confirm M-Pesa prompt",
                "checkout_id": payment["checkout_id"],
            }

        # Step 6: Call Claude with paid request
        ai_response = await self._invoke_claude(prompt, service_type)

        # Step 7: Log transaction
        await self._log_transaction(user_id, payment["checkout_id"], service_type, prompt, ai_response, amount)

        return {
            "success": True,
            "payment_id": payment["checkout_id"],
            "response": ai_response,
            "cost": amount,
        }

    async def _get_ai_decision(self, prompt: str, service_type: str) -> dict[str, Any]:
        """AI decides if payment should be executed."""
        message = await self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"""User request: {prompt}

Service type: {service_type}
Price: {settings.SERVICE_PRICING[service_type]} KES

Decide if this request should trigger a payment. Response format:
{{
  "should_pay": true/false,
  "reason": "explanation"
}}""",
                }
            ],
        )
        try:
            text = message.content[0].text
            # Extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except (json.JSONDecodeError, IndexError):
            return {"should_pay": True, "reason": "Default to payment"}

    async def _check_mpesa_balance(self, phone_number: str) -> int:
        """Check M-Pesa balance for user."""
        # This would call M-Pesa API to check balance
        # For now, return a mock value
        return 1000  # Mock: 1000 KES

    async def _execute_autonomous_payment(self, user_id: int, phone_number: str, amount: int, service_type: str) -> dict[str, Any]:
        """Execute payment autonomously via M-Pesa."""
        from payment import initiate_stk_push

        try:
            payment = await initiate_stk_push(user_id, phone_number, service_type)
            return {
                "success": True,
                "checkout_id": payment.checkout_request_id,
                "amount": amount,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _wait_for_payment(self, checkout_id: str, max_wait: int = 30) -> bool:
        """Poll for payment confirmation."""
        from payment import get_payment_status

        for _ in range(max_wait // 2):
            payment = get_payment_status(checkout_id)
            if payment and payment.status == "paid":
                return True
            await asyncio.sleep(2)
        return False

    async def _invoke_claude(self, prompt: str, service_type: str) -> str:
        """Call Claude API with user prompt."""
        message = await self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=f"You are a {service_type} assistant providing detailed responses.",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if getattr(block, "type", None) == "text")

    async def _log_transaction(self, user_id: int, checkout_id: str, service_type: str, prompt: str, answer: str, amount: int) -> None:
        """Log the transaction to database."""
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO transactions (user_id, checkout_request_id, service_type, prompt, answer, amount, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, checkout_id, service_type, prompt, answer, amount, utc_now()),
            )
            conn.commit()
        finally:
            conn.close()
