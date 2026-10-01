from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    APP_NAME: str = "M-Pesa AI Agent API"
    APP_VERSION: str = "1.0.0"
    MPESA_ENVIRONMENT: str = os.getenv("MPESA_ENVIRONMENT", "sandbox").lower()
    MPESA_BASE_URL: str = (
        "https://api.safaricom.co.ke" if MPESA_ENVIRONMENT == "production" else "https://sandbox.safaricom.co.ke"
    )
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE", "")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL: str = os.getenv("MPESA_CALLBACK_URL", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "backend" / "data" / "app.db"))
    ALLOWED_ORIGINS: list[str] = [
        item.strip() for item in os.getenv("ALLOWED_ORIGINS", "").split(",") if item.strip()
    ]
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    SERVICE_PRICING: dict[str, int] = {
        "basicQuery": 50,
        "advancedAnalysis": 200,
        "customReport": 500,
        "premiumSupport": 1000,
    }


settings = Settings()
