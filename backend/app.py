"""FastAPI service for M-Pesa payments and paid AI requests.

Secrets are loaded from environment variables. This module intentionally contains
no credentials and is not intended to be hosted by GitHub Pages.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

ENVIRONMENT = os.getenv("MPESA_ENVIRONMENT", "sandbox").lower()
MPESA_BASE = "https://api.safaricom.co.ke" if ENVIRONMENT == "production" else "https://sandbox.safaricom.co.ke"
DB_PATH = Path(os.getenv("DATABASE_PATH", "./backend/data/app.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
PRICES = {"basicQuery": 50, "advancedAnalysis": 200, "customReport": 500, "premiumSupport": 1000}

app = FastAPI(title="M-Pesa AI Agent API", version="1.0.0")
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS payments (
        checkout_request_id TEXT PRIMARY KEY,
        merchant_request_id TEXT,
        amount INTEGER NOT NULL,
        phone_number TEXT NOT NULL,
        status TEXT NOT NULL,
        receipt TEXT,
        raw_callback TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    return connection


class StkRequest(BaseModel):
    phone_number: str = Field(pattern=r"^254[17]\\d{8}$")
    amount: int = Field(ge=1, le=150000)
    service_type: str = "basicQuery"


class AIRequest(BaseModel):
    checkout_request_id: str
    query: str = Field(min_length=1, max_length=12000)
    service_type: str = "basicQuery"


async def access_token() -> str:
    key = os.getenv("MPESA_CONSUMER_KEY")
    secret = os.getenv("MPESA_CONSUMER_SECRET")
    if not key or not secret:
        raise HTTPException(503, "M-Pesa credentials are not configured")
    credentials = base64.b64encode(f"{key}:{secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{MPESA_BASE}/oauth/v1/generate?grant_type=client_credentials", headers={"Authorization": f"Basic {credentials}"})
    if response.is_error:
        raise HTTPException(502, "Unable to authenticate with M-Pesa")
    return response.json()["access_token"]


def stk_password(timestamp: str) -> str:
    shortcode = os.environ["MPESA_SHORTCODE"]
    passkey = os.environ["MPESA_PASSKEY"]
    return base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": ENVIRONMENT}


@app.post("/api/payments/stk-push")
async def start_payment(payload: StkRequest) -> dict[str, Any]:
    if payload.service_type not in PRICES or payload.amount != PRICES[payload.service_type]:
        raise HTTPException(400, "Invalid amount or service type")
    shortcode = os.getenv("MPESA_SHORTCODE")
    callback = os.getenv("MPESA_CALLBACK_URL")
    if not shortcode or not os.getenv("MPESA_PASSKEY") or not callback:
        raise HTTPException(503, "M-Pesa payment configuration is incomplete")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    body = {"BusinessShortCode": shortcode, "Password": stk_password(timestamp), "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline", "Amount": payload.amount, "PartyA": payload.phone_number, "PartyB": shortcode, "PhoneNumber": payload.phone_number, "CallBackURL": callback, "AccountReference": f"AI-{payload.service_type}", "TransactionDesc": "AI Agent service"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{MPESA_BASE}/mpesa/stkpush/v1/processrequest", json=body, headers={"Authorization": f"Bearer {await access_token()}"})
    data = response.json()
    if response.is_error or data.get("ResponseCode") != "0":
        raise HTTPException(502, data.get("errorMessage", "STK Push failed"))
    now = datetime.now(timezone.utc).isoformat()
    with db() as connection:
        connection.execute("INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (data["CheckoutRequestID"], data.get("MerchantRequestID"), payload.amount, payload.phone_number, "pending", None, None, now, now))
    return {"checkout_request_id": data["CheckoutRequestID"], "customer_message": data.get("CustomerMessage", "Check your phone")}


@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request) -> dict[str, str]:
    body = await request.json()
    callback = body.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    if not checkout_id:
        return {"ResultCode": "0", "ResultDesc": "Accepted"}
    status = "paid" if callback.get("ResultCode") == 0 else "failed"
    items = callback.get("CallbackMetadata", {}).get("Item", [])
    receipt = next((item.get("Value") for item in items if item.get("Name") == "MpesaReceiptNumber"), None)
    now = datetime.now(timezone.utc).isoformat()
    with db() as connection:
        connection.execute("UPDATE payments SET status=?, receipt=?, raw_callback=?, updated_at=? WHERE checkout_request_id=?", (status, receipt, json.dumps(body), now, checkout_id))
    return {"ResultCode": "0", "ResultDesc": "Accepted"}


@app.get("/api/payments/{checkout_request_id}")
async def payment_status(checkout_request_id: str) -> dict[str, Any]:
    with db() as connection:
        row = connection.execute("SELECT checkout_request_id, amount, status, receipt, updated_at FROM payments WHERE checkout_request_id=?", (checkout_request_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Payment not found")
    return dict(row)


@app.post("/api/ai/query")
async def paid_ai_query(payload: AIRequest) -> dict[str, Any]:
    with db() as connection:
        payment = connection.execute("SELECT amount, status FROM payments WHERE checkout_request_id=?", (payload.checkout_request_id,)).fetchone()
    if not payment or payment["status"] != "paid":
        raise HTTPException(402, "A confirmed M-Pesa payment is required")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(503, "AI provider is not configured")
    client = AsyncAnthropic(api_key=api_key)
    message = await client.messages.create(model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"), max_tokens=1000, system=f"You are a helpful {payload.service_type} assistant.", messages=[{"role": "user", "content": payload.query}])
    answer = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
    return {"answer": answer, "amount": payment["amount"], "checkout_request_id": payload.checkout_request_id}
