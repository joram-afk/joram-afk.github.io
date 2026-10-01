from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone

import httpx
from anthropic import AsyncAnthropic
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import settings
from backend.database import get_connection
from backend.models import (
    AIRequestPayload,
    AIResponse,
    AuthToken,
    LoginPayload,
    PaymentStatusResponse,
    RegisterPayload,
    StkPushPayload,
    TokenResponse,
    UserOut,
    utc_now,
)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

security = HTTPBearer(auto_error=False)

if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token(user_id: int, email: str) -> str:
    payload = {"sub": str(user_id), "email": email, "exp": datetime.now(timezone.utc).timestamp() + 86400}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials | None) -> int:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        return user_id
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc


def token_for_user(user_id: int, email: str) -> str:
    return create_token(user_id, email)


async def get_mpesa_token() -> str:
    if not settings.MPESA_CONSUMER_KEY or not settings.MPESA_CONSUMER_SECRET:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "M-Pesa credentials are not configured")
    auth = base64.b64encode(f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()).decode()
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(
            f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}"},
        )
    if response.is_error:
        raise HTTPException(response.status_code, "M-Pesa authentication failed")
    data = response.json()
    return str(data["access_token"])


def mpesa_password(timestamp: str) -> str:
    if not settings.MPESA_SHORTCODE or not settings.MPESA_PASSKEY:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "M-Pesa passkey or shortcode is missing")
    return base64.b64encode(f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()).decode()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.APP_NAME}


@app.post("/api/auth/register", response_model=AuthToken)
async def register(payload: RegisterPayload) -> AuthToken:
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (payload.email,)).fetchone()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "User already exists")
        now = utc_now()
        password_hash = hash_password(payload.password)
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, full_name, phone_number, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(payload.email), password_hash, payload.full_name, payload.phone_number, now),
        )
        user_id = cursor.lastrowid
        user = conn.execute(
            "SELECT id, email, full_name, phone_number, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    access_token = create_token(user["id"], user["email"])
    return AuthToken(access_token=access_token, user=UserOut(**dict(user)))


@app.post("/api/auth/login", response_model=AuthToken)
async def login(payload: LoginPayload) -> AuthToken:
    password_hash = hash_password(payload.password)
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, email, full_name, phone_number, created_at FROM users WHERE email = ? AND password_hash = ?",
            (str(payload.email), password_hash),
        ).fetchone()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    access_token = create_token(user["id"], user["email"])
    return AuthToken(access_token=access_token, user=UserOut(**dict(user)))


@app.post("/api/payments/stk-push")
async def stk_push(payload: StkPushPayload, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, str | int]:
    user_id = verify_token(credentials)
    amount = int(payload.amount)
    if amount != settings.SERVICE_PRICING.get(payload.service_type, 0):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Amount does not match service price")
    if not settings.MPESA_CALLBACK_URL:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Callback URL is not configured")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    body = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": mpesa_password(timestamp),
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": payload.phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": payload.phone_number,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": f"AI-{payload.service_type}",
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
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, result.get("errorMessage", "STK Push failed"))
    checkout_request_id = result["CheckoutRequestID"]
    merchant_request_id = result.get("MerchantRequestID")
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO payments (checkout_request_id, merchant_request_id, user_id, amount, phone_number, service_type, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (checkout_request_id, merchant_request_id, user_id, amount, payload.phone_number, payload.service_type, "pending", now, now),
        )
    return {"checkout_request_id": checkout_request_id, "customer_message": result.get("CustomerMessage", "Check your phone")}


@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request) -> dict[str, str]:
    payload = await request.json()
    callback_data = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = callback_data.get("CheckoutRequestID")
    if not checkout_id:
        return {"ResultCode": "0", "ResultDesc": "Accepted"}
    status_value = "paid" if callback_data.get("ResultCode") == 0 else "failed"
    receipt = None
    items = callback_data.get("CallbackMetadata", {}).get("Item", [])
    for item in items:
        if item.get("Name") == "MpesaReceiptNumber":
            receipt = item.get("Value")
            break
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            "UPDATE payments SET status = ?, receipt = ?, raw_callback = ?, updated_at = ? WHERE checkout_request_id = ?",
            (status_value, receipt, json.dumps(payload), now, checkout_id),
        )
    return {"ResultCode": "0", "ResultDesc": "Accepted"}


@app.get("/api/payments/{checkout_request_id}", response_model=PaymentStatusResponse)
async def payment_status(checkout_request_id: str) -> PaymentStatusResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT checkout_request_id, merchant_request_id, user_id, amount, phone_number, service_type, status, receipt, created_at, updated_at FROM payments WHERE checkout_request_id = ?",
            (checkout_request_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    return PaymentStatusResponse(**dict(row))


@app.post("/api/ai/invoke", response_model=AIResponse)
async def invoke_ai(payload: AIRequestPayload, credentials: HTTPAuthorizationCredentials = Depends(security)) -> AIResponse:
    verify_token(credentials)
    with get_connection() as conn:
        payment = conn.execute(
            "SELECT amount, status FROM payments WHERE checkout_request_id = ?",
            (payload.checkout_request_id,),
        ).fetchone()
    if payment is None or payment["status"] != "paid":
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "A confirmed M-Pesa payment is required")
    if payload.service_type not in settings.SERVICE_PRICING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported service type")
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Anthropic API key is not configured")
    message = await client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=f"You are a helpful {payload.service_type} assistant.",
        messages=[{"role": "user", "content": payload.query}],
    )
    answer = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
    return AIResponse(answer=answer, amount=int(payment["amount"]), checkout_request_id=payload.checkout_request_id)
