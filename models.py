from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

ServiceType = Literal["basicQuery", "advancedAnalysis", "customReport", "premiumSupport"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class User:
    def __init__(self, user_id: int, email: str, full_name: str, phone_number: str | None = None, created_at: str = ""):
        self.id = user_id
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.created_at = created_at

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} name={self.full_name}>"


class Payment:
    def __init__(
        self,
        checkout_request_id: str,
        user_id: int,
        amount: int,
        phone_number: str,
        service_type: str,
        status: str,
        created_at: str = "",
        merchant_request_id: str | None = None,
        receipt: str | None = None,
    ):
        self.checkout_request_id = checkout_request_id
        self.merchant_request_id = merchant_request_id
        self.user_id = user_id
        self.amount = amount
        self.phone_number = phone_number
        self.service_type = service_type
        self.status = status
        self.receipt = receipt
        self.created_at = created_at

    def __repr__(self) -> str:
        return f"<Payment id={self.checkout_request_id} status={self.status} amount={self.amount}>"


class Transaction:
    def __init__(
        self,
        user_id: int,
        service_type: str,
        prompt: str,
        answer: str,
        amount: int,
        checkout_request_id: str | None = None,
        created_at: str = "",
    ):
        self.user_id = user_id
        self.checkout_request_id = checkout_request_id
        self.service_type = service_type
        self.prompt = prompt
        self.answer = answer
        self.amount = amount
        self.created_at = created_at

    def __repr__(self) -> str:
        return f"<Transaction user={self.user_id} service={self.service_type} amount={self.amount}>"
