from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

from database import get_connection
from config import settings


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def grant_mpesa_access(
    user_id: int,
    max_per_transaction: int,
    max_daily_total: int,
    valid_days: int = 30,
) -> str:
    """Grant temporary access for AI to request M-Pesa payments within configured limits."""
    now = datetime.now(timezone.utc)
    expires_at = (now.timestamp() + (valid_days * 24 * 60 * 60))
    token = hashlib.sha256(f"{user_id}:{now.isoformat()}:{os.urandom(16).hex()}".encode()).hexdigest()

    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mpesa_access (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                max_per_transaction INTEGER NOT NULL,
                max_daily_total INTEGER NOT NULL,
                granted_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO mpesa_access (token, user_id, max_per_transaction, max_daily_total, granted_at, expires_at, revoked) VALUES (?, ?, ?, ?, ?, ?, 0)",
            (
                token,
                user_id,
                max_per_transaction,
                max_daily_total,
                now.isoformat(),
                datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return token


def revoke_mpesa_access(token: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE mpesa_access SET revoked = 1 WHERE token = ?",
            (token,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_mpesa_access(token: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT token, user_id, max_per_transaction, max_daily_total, granted_at, expires_at, revoked FROM mpesa_access WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def validate_mpesa_access(token: str, amount: int) -> tuple[bool, str | None, int | None]:
    access = get_mpesa_access(token)
    if access is None:
        return False, "Invalid access token", None
    if access["revoked"]:
        return False, "Access token has been revoked", None

    now = datetime.now(timezone.utc)
    expiry = datetime.fromisoformat(access["expires_at"])
    if now > expiry:
        return False, "Access token has expired", None

    if amount > access["max_per_transaction"]:
        return False, f"Amount exceeds max per transaction of {access['max_per_transaction']} KES", None

    # Daily total check
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE user_id = ? AND status = 'paid' AND created_at >= ?",
            (
                access["user_id"],
                datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
            ),
        ).fetchone()
        current_total = int(row["total"] or 0)
    finally:
        conn.close()

    if current_total + amount > access["max_daily_total"]:
        return False, f"Amount exceeds remaining daily total of {access['max_daily_total'] - current_total} KES", None

    return True, None, access["user_id"]
