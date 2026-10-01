from __future__ import annotations

import sqlite3
from pathlib import Path

from config import settings

DB_PATH = Path(settings.DATABASE_PATH)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone_number TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                checkout_request_id TEXT PRIMARY KEY,
                merchant_request_id TEXT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                service_type TEXT NOT NULL,
                status TEXT NOT NULL,
                receipt TEXT,
                raw_callback TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                checkout_request_id TEXT,
                service_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                answer TEXT NOT NULL,
                amount INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
