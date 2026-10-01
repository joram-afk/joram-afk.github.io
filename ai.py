from __future__ import annotations

from anthropic import AsyncAnthropic

from config import settings
from database import get_connection
from models import Transaction, utc_now


async def invoke_ai(user_id: int, checkout_request_id: str, prompt: str, service_type: str) -> Transaction:
    """Invoke Claude AI for a paid query."""
    # Verify payment
    conn = get_connection()
    try:
        payment = conn.execute(
            "SELECT amount, status FROM payments WHERE checkout_request_id = ?",
            (checkout_request_id,),
        ).fetchone()
    finally:
        conn.close()
    
    if payment is None or payment["status"] != "paid":
        raise ValueError("Payment not confirmed")
    
    # Call Anthropic
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("Anthropic API key is not configured")
    
    message = await client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=f"You are a helpful {service_type} assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    
    answer = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
    now = utc_now()
    
    # Log transaction
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO transactions (user_id, checkout_request_id, service_type, prompt, answer, amount, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, checkout_request_id, service_type, prompt, answer, payment["amount"], now),
        )
        conn.commit()
    finally:
        conn.close()
    
    return Transaction(
        user_id=user_id,
        checkout_request_id=checkout_request_id,
        service_type=service_type,
        prompt=prompt,
        answer=answer,
        amount=payment["amount"],
        created_at=now,
    )


def get_user_transactions(user_id: int) -> list[Transaction]:
    """Get all transactions for a user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT user_id, checkout_request_id, service_type, prompt, answer, amount, created_at FROM transactions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            Transaction(
                user_id=row["user_id"],
                checkout_request_id=row["checkout_request_id"],
                service_type=row["service_type"],
                prompt=row["prompt"],
                answer=row["answer"],
                amount=row["amount"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    finally:
        conn.close()
