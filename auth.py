from __future__ import annotations

import hashlib

from database import get_connection
from models import User, utc_now


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(email: str, password: str, full_name: str, phone_number: str | None = None) -> User:
    """Register a new user."""
    password_hash = hash_password(password)
    now = utc_now()
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, full_name, phone_number, created_at) VALUES (?, ?, ?, ?, ?)",
            (email, password_hash, full_name, phone_number, now),
        )
        conn.commit()
        user_id = cursor.lastrowid
        return User(user_id, email, full_name, phone_number, now)
    except Exception as e:
        raise RuntimeError(f"Registration failed: {str(e)}") from e
    finally:
        conn.close()


def login_user(email: str, password: str) -> User:
    """Authenticate a user."""
    password_hash = hash_password(password)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, full_name, phone_number, created_at FROM users WHERE email = ? AND password_hash = ?",
            (email, password_hash),
        ).fetchone()
        if row is None:
            raise ValueError("Invalid email or password")
        return User(**dict(row))
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> User | None:
    """Fetch user by ID."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, full_name, phone_number, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return User(**dict(row))
    finally:
        conn.close()


def get_user_by_email(email: str) -> User | None:
    """Fetch user by email."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, full_name, phone_number, created_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row is None:
            return None
        return User(**dict(row))
    finally:
        conn.close()
