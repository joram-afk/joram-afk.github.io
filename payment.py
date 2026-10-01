from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

import httpx

from config import settings
from database import get_connection
from models import Payment, utc_now


async def get_mpesa_token() -> str:
    """Get M-Pesa access token."""
    if not settings.MPESA_CONSUMER_KEY or not settings.MPESA_CONSUMER_SECRET:
        raise RuntimeError("M-Pesa credentials are not configured")
    auth = base64.b64encode(f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()).decode()
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(
            f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}"},
        )
    if response.is_error:
        raise RuntimeError(f"M-Pesa auth failed: {response.text}")
    data = response.json()
    return str(data["access_token"])


def mpesa_password(timestamp: str) -> str:
    """Generate M-Pesa password for STK push."""
    if not settings.MPESA_SHORTCODE or not settings.MPESA_PASSKEY:
        raise RuntimeError("M-Pesa configuration is incomplete")
    return base64.b64encode(f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()).decode()


async def initiate_stk_push(user_id: int, phone_number: str, service_type: str) -> Payment:
    """Initiate M-Pesa STK push."""
    if service_type not in settings.SERVICE_PRICING:
        raise ValueError(f"Unknown service type: {service_type}")
    
    amount = settings.SERVICE_PRICING[service_type]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    
    body = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": mpesa_password(timestamp),
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": "https://example.com/api/callback",  # Replace with your URL
        "AccountReference": f"AI-{service_type}",
        "TransactionDesc": "AI Agent service",
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=body,
            headers={"Authorization": f"Bearer {await get_mpesa_token()}"},
        )
    
    result = response.json()
    if response.is_error or result.get("ResponseCode") != "0":
        raise RuntimeError(f"STK push failed: {result.get('errorMessage', 'Unknown error')}")
    
    checkout_request_id = result["CheckoutRequestID"]
    merchant_request_id = result.get("MerchantRequestID")
    now = utc_now()
    
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO payments (checkout_request_id, merchant_request_id, user_id, amount, phone_number, service_type, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (checkout_request_id, merchant_request_id, user_id, amount, phone_number, service_type, "pending", now, now),
        )
        conn.commit()
    finally:
        conn.close()
    
    return Payment(
        checkout_request_id=checkout_request_id,
        user_id=user_id,
        amount=amount,
        phone_number=phone_number,
        service_type=service_type,
        status="pending",
        created_at=now,
        merchant_request_id=merchant_request_id,
    )


def get_payment_status(checkout_request_id: str) -> Payment | None:
    """Get payment status."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT checkout_request_id, merchant_request_id, user_id, amount, phone_number, service_type, status, receipt, created_at, updated_at FROM payments WHERE checkout_request_id = ?",
            (checkout_request_id,),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        return Payment(
            checkout_request_id=data["checkout_request_id"],
            merchant_request_id=data["merchant_request_id"],
            user_id=data["user_id"],
            amount=data["amount"],
            phone_number=data["phone_number"],
            service_type=data["service_type"],
            status=data["status"],
            receipt=data["receipt"],
            created_at=data["created_at"],
        )
    finally:
        conn.close()
