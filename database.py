"""Database module for payment tracking using SQLite."""

import re

import aiosqlite

from config import settings


def _safe_network_name(name: str) -> str:
    """Validate that a network name is safe for use in SQL DEFAULT clauses.

    SQLite does not support parameterised DEFAULT values in CREATE TABLE
    or ALTER TABLE, so we must interpolate the string.  This helper
    ensures only alphanumeric characters and hyphens are allowed, preventing
    any SQL injection.

    Raises:
        ValueError: If the name contains unsafe characters.
    """
    if not re.fullmatch(r"[a-zA-Z0-9\-]+", name):
        raise ValueError(
            f"Unsafe network name for SQL default: '{name}'. "
            "Only [a-zA-Z0-9-] are allowed."
        )
    return name


async def init_db() -> None:
    """Initialize the database and create tables if they don't exist."""
    safe_default = _safe_network_name(settings.default_network)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                receiver TEXT NOT NULL,
                token_id TEXT NOT NULL DEFAULT 'usdc',
                network TEXT NOT NULL DEFAULT '{safe_default}',
                status TEXT NOT NULL DEFAULT 'pending',
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migration: add columns if missing (for existing databases)
        cursor = await db.execute("PRAGMA table_info(payments)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "token_id" not in columns:
            await db.execute(
                "ALTER TABLE payments ADD COLUMN token_id TEXT NOT NULL DEFAULT 'usdc'"
            )
        if "network" not in columns:
            await db.execute(
                "ALTER TABLE payments "
                f"ADD COLUMN network TEXT NOT NULL DEFAULT '{safe_default}'"
            )
        await db.commit()


async def create_payment(
    payment_id: str,
    amount: float,
    receiver: str,
    token_id: str = "usdc",
    network: str | None = None,
) -> None:
    """Create a new payment record.

    Args:
        payment_id: Unique identifier for the payment.
        amount: Payment amount.
        receiver: Blockchain address to receive the payment.
        token_id: Token identifier (e.g. "usdc", "kii").
        network: Network name (e.g. "base", "base-sepolia").
            Defaults to DEFAULT_NETWORK from settings.
    """
    resolved_network = network or settings.default_network
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO payments "
            "(payment_id, amount, receiver, token_id, network, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (payment_id, amount, receiver, token_id, resolved_network, "pending"),
        )
        await db.commit()


async def get_payment(payment_id: str) -> dict | None:
    """Get payment details by payment ID.

    Args:
        payment_id: Unique identifier for the payment.

    Returns:
        Payment record as a dictionary, or None if not found.
    """
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def update_payment_status(
    payment_id: str, status: str, tx_hash: str | None = None
) -> None:
    """Update payment status and optionally the transaction hash.

    Args:
        payment_id: Unique identifier for the payment.
        status: New status (pending, paid, failed).
        tx_hash: Optional transaction hash from successful payment.
    """
    async with aiosqlite.connect(settings.database_path) as db:
        if tx_hash:
            await db.execute(
                """
                UPDATE payments
                SET status = ?, tx_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE payment_id = ?
                """,
                (status, tx_hash, payment_id),
            )
        else:
            await db.execute(
                """
                UPDATE payments
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE payment_id = ?
                """,
                (status, payment_id),
            )
        await db.commit()
