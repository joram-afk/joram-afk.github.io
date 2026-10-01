from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field

ServiceType = Literal["basicQuery", "advancedAnalysis", "customReport", "premiumSupport"]


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str | None = Field(default=None, min_length=10, max_length=20)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class StkPushPayload(BaseModel):
    phone_number: str = Field(pattern=r"^254[17]\d{8}$")
    amount: int = Field(ge=1, le=150000)
    service_type: ServiceType = "basicQuery"


class AIRequestPayload(BaseModel):
    checkout_request_id: str
    query: str = Field(min_length=1, max_length=12000)
    service_type: ServiceType = "basicQuery"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PaymentStatusResponse(BaseModel):
    checkout_request_id: str
    merchant_request_id: str | None = None
    amount: int
    phone_number: str
    service_type: str
    status: str
    receipt: str | None = None
    created_at: str
    updated_at: str


class AIResponse(BaseModel):
    answer: str
    amount: int
    checkout_request_id: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone_number: str | None = None
    created_at: str


class AuthToken(BaseModel):
    access_token: str
    user: UserOut


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
