
import sqlite3
import uuid
from datetime import datetime, timezone

from database import DATABASE_PATH


SUPPORTED_CURRENCIES = ("ETB", "USD")
SUPPORTED_PROVIDERS = ("TELEBIRR", "CBE_BIRR")


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_wallet_database():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                wallet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                currency TEXT NOT NULL
                    CHECK(currency IN ('ETB', 'USD')),
                balance_minor INTEGER NOT NULL DEFAULT 0
                    CHECK(balance_minor >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, currency),
                FOREIGN KEY(player_id)
                    REFERENCES players(player_id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_ref TEXT NOT NULL UNIQUE,
                player_id INTEGER NOT NULL,
                currency TEXT NOT NULL
                    CHECK(currency IN ('ETB', 'USD')),
                transaction_type TEXT NOT NULL,
                amount_minor INTEGER NOT NULL
                    CHECK(amount_minor > 0),
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN (
                        'pending', 'completed', 'failed', 'reversed'
                    )),
                provider TEXT,
                provider_reference TEXT UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY(player_id)
                    REFERENCES players(player_id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_wallet_transactions_player
            ON wallet_transactions(player_id, created_at)
        """)

        connection.commit()
        print("Wallet database initialized successfully.")

    finally:
        connection.close()


def create_wallet_accounts(player_id):
    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        player = connection.execute("""
            SELECT player_id
            FROM players
            WHERE player_id = ?
        """, (player_id,)).fetchone()

        if player is None:
            return False

        for currency in SUPPORTED_CURRENCIES:
            connection.execute("""
                INSERT OR IGNORE INTO wallets
                    (player_id, currency)
                VALUES (?, ?)
            """, (player_id, currency))

        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_wallets(player_id):
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT currency, balance_minor, created_at
            FROM wallets
            WHERE player_id = ?
            ORDER BY currency
        """, (player_id,)).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def create_pending_deposit(
    player_id,
    currency,
    amount_minor,
    provider
):
    currency = currency.upper()
    provider = provider.upper()

    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError("Unsupported currency.")

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError("Unsupported payment provider.")

    if not isinstance(amount_minor, int) or amount_minor <= 0:
        raise ValueError("Amount must be a positive integer in minor units.")

    transaction_ref = "ZG-" + uuid.uuid4().hex.upper()

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        player = connection.execute("""
            SELECT player_id
            FROM players
            WHERE player_id = ?
        """, (player_id,)).fetchone()

        if player is None:
            raise ValueError("Player is not registered.")

        connection.execute("""
            INSERT OR IGNORE INTO wallets
                (player_id, currency)
            VALUES (?, ?)
        """, (player_id, currency))

        connection.execute("""
            INSERT INTO wallet_transactions (
                transaction_ref,
                player_id,
                currency,
                transaction_type,
                amount_minor,
                status,
                provider,
                description
            )
            VALUES (?, ?, ?, 'deposit', ?, 'pending', ?, ?)
        """, (
            transaction_ref,
            player_id,
            currency,
            amount_minor,
            provider,
            "Awaiting verified provider confirmation"
        ))

        connection.commit()
        return transaction_ref

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_wallet_transactions(player_id, limit=20):
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100.")

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                transaction_ref,
                currency,
                transaction_type,
                amount_minor,
                status,
                provider,
                provider_reference,
                description,
                created_at,
                completed_at
            FROM wallet_transactions
            WHERE player_id = ?
            ORDER BY transaction_id DESC
            LIMIT ?
        """, (player_id, limit)).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()
